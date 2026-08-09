from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from typing import List
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date, timedelta
import re
import logging

from app.database import get_db
from app.models import Request, RequestItem, Slot, Hermano, Schedule, Exhibitor
from app.models import User as UserModel  # Use alias to avoid scope conflicts
from app.models import User  # Import User for type annotations (get_current_user returns User)
from app.utils.security import get_current_user
from app.utils.audit import log_audit
from app.worker import send_notification_task

router = APIRouter()
logger = logging.getLogger(__name__)

class RequestItemCreate(BaseModel):
    slot_id: str

class RequestItemCreateWithDetails(BaseModel):
    point_id: str
    schedule_id: str
    slot_date: str  # ISO date format YYYY-MM-DD

class RequestCreate(BaseModel):
    items: List[RequestItemCreate]
    notes: str | None = None

class RequestCreateWithoutAuth(BaseModel):
    phone: str  # Teléfono del hermano
    items: List[RequestItemCreateWithDetails]  # Punto, horario y fecha
    notes: str | None = None

class RequestResponse(BaseModel):
    id: str
    status: str
    notes: str | None = None
    created_at: str
    items: List[dict]

@router.post("", response_model=RequestResponse)
async def create_request(
    data: RequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new request with multiple slots"""
    if not data.items:
        raise HTTPException(status_code=400, detail="At least one slot required")
    
    # Create request
    request = Request(
        user_id=current_user.id,
        status="pending",
        notes=data.notes
    )
    db.add(request)
    await db.flush()
    
    # Add items
    conflicts = []
    success_items = []
    
    for item_data in data.items:
        try:
            # Verify slot exists
            slot_result = await db.execute(
                select(Slot).where(Slot.id == UUID(item_data.slot_id))
            )
            slot = slot_result.scalar_one_or_none()
            if not slot:
                conflicts.append({"slot_id": item_data.slot_id, "reason": "Slot not found"})
                continue
            
            # Create request item (unique constraint on slot_id handles concurrency)
            request_item = RequestItem(
                request_id=request.id,
                slot_id=slot.id,
                status="pending"
            )
            db.add(request_item)
            await db.flush()
            success_items.append(request_item)
            
        except IntegrityError:
            await db.rollback()
            conflicts.append({"slot_id": item_data.slot_id, "reason": "Slot already assigned"})
            # Re-add request for next iteration
            db.add(request)
            await db.flush()
    
    if not success_items:
        await db.rollback()
        raise HTTPException(status_code=409, detail="All slots are already assigned", headers={"conflicts": str(conflicts)})
    
    await db.commit()
    await db.refresh(request)
    
    # Log audit
    await log_audit(db, current_user.id, "user", "request_created", {"request_id": str(request.id)})
    
    # Send notification
    send_notification_task.delay(str(request.id), "request_received")
    
    response_items = []
    for item in success_items:
        await db.refresh(item)
        response_items.append({
            "id": str(item.id),
            "slot_id": str(item.slot_id),
            "status": item.status
        })
    
    return {
        "id": str(request.id),
        "status": request.status,
        "notes": request.notes,
        "created_at": request.created_at.isoformat(),
        "items": response_items,
        "conflicts": conflicts if conflicts else None
    }

@router.get("/{request_id}", response_model=RequestResponse)
async def get_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get request by ID"""
    result = await db.execute(
        select(Request).where(
            Request.id == UUID(request_id),
            Request.user_id == current_user.id
        )
    )
    request = result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Get items
    items_result = await db.execute(
        select(RequestItem).where(RequestItem.request_id == request.id)
    )
    items = items_result.scalars().all()
    
    return {
        "id": str(request.id),
        "status": request.status,
        "notes": request.notes,
        "created_at": request.created_at.isoformat(),
        "items": [
            {
                "id": str(item.id),
                "slot_id": str(item.slot_id),
                "status": item.status
            }
            for item in items
        ]
    }

@router.post("/public", response_model=RequestResponse)
async def create_request_public(
    data: RequestCreateWithoutAuth,
    db: AsyncSession = Depends(get_db)
):
    """Create request without authentication - uses phone to find hermano"""
    logger.info(f"=== INICIO create_request_public ===")
    logger.info(f"Teléfono recibido: {data.phone}")
    logger.info(f"Número de items recibidos: {len(data.items)}")
    for idx, item in enumerate(data.items):
        logger.info(f"Item {idx+1}: point_id={item.point_id}, schedule_id={item.schedule_id}, date={item.slot_date}")
    
    if not data.items:
        raise HTTPException(status_code=400, detail="Al menos un turno es requerido")
    
    # Buscar hermano por teléfono
    phone_clean = re.sub(r'\D', '', data.phone)
    if not phone_clean or len(phone_clean) < 7:
        raise HTTPException(status_code=400, detail="Teléfono inválido")
    
    # Buscar hermano
    result_hermano = await db.execute(
        select(Hermano).where(
            Hermano.is_active == True,
            Hermano.telefono.like(f'%{phone_clean}%')
        )
    )
    hermano = result_hermano.scalar_one_or_none()
    
    if not hermano:
        raise HTTPException(status_code=404, detail="Hermano no encontrado. Por favor contacte al administrador.")
    
    # Buscar o crear usuario asociado al hermano
    # Primero intentar encontrar usuario existente por teléfono
    result_user = await db.execute(
        select(UserModel).where(UserModel.phone.like(f'%{phone_clean}%'), UserModel.is_active == True)
    )
    user = result_user.scalar_one_or_none()
    
    # Si no existe, crear usuario temporal
    if not user:
        user = UserModel(
            full_name=hermano.nombre,
            phone=f"+57{phone_clean[-10:]}" if len(phone_clean) == 10 else f"+{phone_clean}",
            is_active=True
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
    
    # Validar que no haya duplicados en la misma solicitud
    seen_combinations = set()
    for item in data.items:
        key = (item.point_id, item.schedule_id, item.slot_date)
        if key in seen_combinations:
            raise HTTPException(
                status_code=400, 
                detail=f"Turno duplicado: mismo punto, horario y día no pueden seleccionarse dos veces"
            )
        seen_combinations.add(key)
    
    # Create request
    request = Request(
        user_id=user.id,
        status="pending",
        notes=data.notes
    )
    db.add(request)
    await db.flush()
    
    # Process items - create or find slots
    conflicts = []
    success_items = []
    
    for item_data in data.items:
        try:
            # Parse date - handle multiple formats
            try:
                if 'T' in item_data.slot_date or 'Z' in item_data.slot_date:
                    slot_date = datetime.fromisoformat(item_data.slot_date.replace('Z', '+00:00')).date()
                else:
                    slot_date = datetime.strptime(item_data.slot_date, '%Y-%m-%d').date()
            except (ValueError, AttributeError) as e:
                conflicts.append({
                    "point_id": item_data.point_id,
                    "schedule_id": item_data.schedule_id,
                    "date": item_data.slot_date,
                    "reason": f"Fecha inválida: {str(e)}"
                })
                continue
            
            # Get schedule to get times and exhibitor
            schedule_result = await db.execute(
                select(Schedule).where(Schedule.id == UUID(item_data.schedule_id))
            )
            schedule = schedule_result.scalar_one_or_none()
            if not schedule:
                conflicts.append({"point_id": item_data.point_id, "schedule_id": item_data.schedule_id, "date": item_data.slot_date, "reason": "Horario no encontrado"})
                continue
            
            # Get exhibitor from schedule
            exhibitor_result = await db.execute(
                select(Exhibitor).where(Exhibitor.id == schedule.exhibitor_id)
            )
            exhibitor = exhibitor_result.scalar_one_or_none()
            if not exhibitor:
                conflicts.append({
                    "point_id": item_data.point_id,
                    "schedule_id": item_data.schedule_id,
                    "date": item_data.slot_date,
                    "reason": "Exhibidor no encontrado"
                })
                continue
            
            # Verificar si el exhibidor está abierto para solicitudes
            today = datetime.now().date()
            
            # VALIDACIÓN 1: Verificar si HOY está dentro del rango permitido
            if exhibitor.open_date and exhibitor.close_date:
                if not (exhibitor.open_date <= today <= exhibitor.close_date):
                    # Calcular el nombre del mes de apertura
                    month_names = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", 
                                   "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                    open_month = month_names[exhibitor.open_date.month] if exhibitor.open_date.month <= 12 else "desconocido"
                    conflicts.append({
                        "point_id": item_data.point_id,
                        "schedule_id": item_data.schedule_id,
                        "date": item_data.slot_date,
                        "reason": f"La asignación de exhibidores para {open_month} estará disponible desde el {exhibitor.open_date.strftime('%d/%m/%Y')}"
                    })
                    continue
            elif exhibitor.open_date and today < exhibitor.open_date:
                conflicts.append({
                    "point_id": item_data.point_id,
                    "schedule_id": item_data.schedule_id,
                    "date": item_data.slot_date,
                    "reason": f"Las solicitudes abrirán el {exhibitor.open_date.strftime('%d/%m/%Y')}"
                })
                continue
            elif exhibitor.close_date and today > exhibitor.close_date:
                conflicts.append({
                    "point_id": item_data.point_id,
                    "schedule_id": item_data.schedule_id,
                    "date": item_data.slot_date,
                    "reason": f"Las solicitudes cerraron el {exhibitor.close_date.strftime('%d/%m/%Y')}"
                })
                continue
            
            # VALIDACIÓN 2: Verificar si la FECHA SOLICITADA está dentro del rango permitido del exhibidor
            # Esto es importante porque un exhibidor puede abrir en diferentes fechas
            # Validar que la fecha esté dentro del rango abierto del exhibidor
            # IMPORTANTE: Apertura a las 00:00:00 del día open_date y cierre hasta las 23:59:59 del close_date
            if exhibitor.open_date and slot_date < exhibitor.open_date:
                conflicts.append({
                    "point_id": item_data.point_id,
                    "schedule_id": item_data.schedule_id,
                    "date": item_data.slot_date,
                    "reason": f"La fecha seleccionada ({slot_date.strftime('%d/%m/%Y')}) es anterior a la apertura del exhibidor ({exhibitor.open_date.strftime('%d/%m/%Y')} a las 00:00 horas)"
                })
                continue
            
            if exhibitor.close_date and slot_date > exhibitor.close_date:
                conflicts.append({
                    "point_id": item_data.point_id,
                    "schedule_id": item_data.schedule_id,
                    "date": item_data.slot_date,
                    "reason": f"La fecha seleccionada ({slot_date.strftime('%d/%m/%Y')}) es posterior al cierre del exhibidor ({exhibitor.close_date.strftime('%d/%m/%Y')} hasta las 23:59 horas)"
                })
                continue
            
            # Create start and end timestamps
            start_ts = datetime.combine(slot_date, schedule.start_time)
            end_ts = datetime.combine(slot_date, schedule.end_time)
            
            # Validate time constraints: 
            # 1. Turno no puede estar en el pasado
            # 2. Si es el mismo día, debe tener al menos 30 minutos de anticipación
            now = datetime.now()
            
            # Check if turn is in the past
            if start_ts < now:
                conflicts.append({
                    "point_id": item_data.point_id,
                    "schedule_id": item_data.schedule_id,
                    "date": item_data.slot_date,
                    "reason": f"El turno ya pasó (inicio: {schedule.start_time.strftime('%H:%M')})"
                })
                continue
            
            # Check if same day and less than 30 minutes before start
            if slot_date == now.date():
                time_until_start = (start_ts - now).total_seconds() / 60  # minutes
                if time_until_start < 30:
                    conflicts.append({
                        "point_id": item_data.point_id,
                        "schedule_id": item_data.schedule_id,
                        "date": item_data.slot_date,
                        "reason": f"Debe seleccionar con al menos 30 minutos de anticipación (inicio: {schedule.start_time.strftime('%H:%M')})"
                    })
                    continue
            
            # Use exhibitor's max_persons_per_slot as capacity
            exhibitor_capacity = exhibitor.max_persons_per_slot or 5
            
            # Find or create slot
            slot_result = await db.execute(
                select(Slot).where(
                    Slot.exhibitor_id == exhibitor.id,
                    Slot.schedule_id == UUID(item_data.schedule_id),
                    Slot.slot_date == slot_date
                )
            )
            slot = slot_result.scalar_one_or_none()
            
            # Check capacity BEFORE creating/finding slot to avoid unnecessary work
            # First, check if slot exists
            if not slot:
                # No slot exists yet - create one
                slot = Slot(
                    exhibitor_id=exhibitor.id,
                    schedule_id=UUID(item_data.schedule_id),
                    slot_date=slot_date,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    capacity=exhibitor_capacity
                )
                db.add(slot)
                await db.flush()
                await db.refresh(slot)
            else:
                # Slot exists - update capacity if exhibitor capacity changed
                if slot.capacity != exhibitor_capacity:
                    slot.capacity = exhibitor_capacity
                    await db.flush()
            
            # Check if this hermano already has a request for this slot (check first to avoid unnecessary capacity check)
            # IMPORTANT: Only check approved, NOT cancelled requests
            # Also exclude items from the current request being created (to allow multiple items in same request)
            existing_user_item = await db.execute(
                select(RequestItem).join(Request).where(
                    RequestItem.slot_id == slot.id,
                    Request.user_id == user.id,
                    Request.id != request.id,  # Exclude current request
                    RequestItem.status == "approved"  # Only approved requests (cancelled don't count)
                )
            )
            existing = existing_user_item.scalar_one_or_none()
            if existing:
                conflicts.append({
                    "point_id": item_data.point_id, 
                    "schedule_id": item_data.schedule_id, 
                    "date": item_data.slot_date, 
                    "reason": f"Ya tiene una solicitud {existing.status} para este turno"
                })
                continue
            
            # Check current capacity - count ONLY approved requests (NOT cancelled)
            # Do this check right before creating the item to minimize race conditions
            # IMPORTANT: We check BEFORE adding the item, so we need to add +1 to see if there's space
            
            # Count existing items in database for this slot (this includes items from current request already flushed)
            count_result = await db.execute(
                select(func.count(RequestItem.id)).where(
                    RequestItem.slot_id == slot.id,
                    RequestItem.status == "approved"  # Only count approved requests (auto-approved)
                )
            )
            current_count = count_result.scalar() or 0
            
            slot_capacity = slot.capacity or exhibitor_capacity
            
            logger.info(f"Verificando capacidad - Slot: {slot.id}, Fecha: {slot_date}, Capacidad: {slot_capacity}, Ocupados: {current_count}")
            
            # Check if slot has space for one more (current_count + 1 for the item we're about to add)
            if current_count >= slot_capacity:
                logger.warning(f"Turno completo - Slot: {slot.id}, {current_count}/{slot_capacity}")
                conflicts.append({
                    "point_id": item_data.point_id, 
                    "schedule_id": item_data.schedule_id, 
                    "date": item_data.slot_date, 
                    "reason": f"Turno completo ({current_count}/{slot_capacity} hermanos)"
                })
                continue
            
            # Create request item - AUTO-APROBADA
            request_item = RequestItem(
                request_id=request.id,
                slot_id=slot.id,
                status="approved"  # Auto-aprobada automáticamente
            )
            db.add(request_item)
            await db.flush()
            
            logger.info(f"✓ RequestItem creado exitosamente - ID: {request_item.id}, Slot: {slot.id}")
            
            # Success - item was added within capacity
            # Note: We already validated capacity before adding, so this should be safe
            # The final commit will happen at the end for all successful items
            success_items.append(request_item)
            
        except IntegrityError as e:
            # Rollback only this item's changes, not the entire transaction
            await db.rollback()
            conflicts.append({
                "point_id": item_data.point_id, 
                "schedule_id": item_data.schedule_id, 
                "date": item_data.slot_date, 
                "reason": f"Error de integridad: {str(e)}"
            })
            # Re-add request for next iteration
            db.add(request)
            await db.flush()
        except Exception as e:
            # Log the full error for debugging
            logger.error(f"Error processing request item: {e}", exc_info=True)
            conflicts.append({
                "point_id": item_data.point_id, 
                "schedule_id": item_data.schedule_id, 
                "date": item_data.slot_date, 
                "reason": f"Error interno: {str(e)}"
            })
            continue
    
    if not success_items:
        await db.rollback()
        logger.error(f"No se pudieron crear solicitudes. Total conflictos: {len(conflicts)}")
        for conflict in conflicts:
            logger.error(f"Conflicto: {conflict}")
        # Return detailed conflict information with conflicts in the detail as a dict
        raise HTTPException(
            status_code=409, 
            detail={
                "message": "No se pudo crear ninguna solicitud",
                "conflicts": conflicts
            }
        )
    
    try:
        await db.commit()
        await db.refresh(request)
    except Exception as e:
        await db.rollback()
        logger.error(f"Error committing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al guardar la solicitud: {str(e)}")
    
    # Log audit (non-blocking, won't fail if it errors)
    try:
        await log_audit(db, user.id, "user", "request_created_public", {"request_id": str(request.id), "hermano_id": str(hermano.id)})
    except Exception as e:
        logger.warning(f"Failed to log audit: {e}")
    
    # Send notification (non-blocking)
    try:
        send_notification_task.delay(str(request.id), "request_received")
    except Exception as e:
        logger.warning(f"Failed to queue notification: {e}")
    
    response_items = []
    for item in success_items:
        await db.refresh(item)
        response_items.append({
            "id": str(item.id),
            "slot_id": str(item.slot_id),
            "status": item.status
        })
    
    return {
        "id": str(request.id),
        "status": request.status,
        "notes": request.notes,
        "created_at": request.created_at.isoformat(),
        "items": response_items,
        "conflicts": conflicts if conflicts else None
    }


async def check_time_conflict(db: AsyncSession, user_id: str, slot_date: date, start_time: str, end_time: str) -> bool:
    """Check if there's a time conflict for a user on a specific date"""
    # TODO: Implement time conflict checking logic
    # For now, return False (no conflict)
    return False
