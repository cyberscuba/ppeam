from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List
from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime

from app.database import get_db
from app.models import Request, RequestItem, User, Admin, Exhibitor, Schedule, Hermano, Slot, ExhibitorLeader
from app.utils.gender_detector import detect_gender_from_name, get_gender_label
from app.utils.security import get_current_user
from app.utils.audit import log_audit
from app.worker import send_notification_task, notify_slot_liberated_task
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db)
) -> Admin:
    """Verify user is admin - supports both user_id and hermano_id"""
    from app.utils.security import security
    from jose import jwt
    from app.config import settings
    
    # Decode token to check is_admin flag
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        # Check if token has admin flag
        if not payload.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # If token has hermano prefix, find admin by hermano_id
        if user_id_str.startswith("hermano_"):
            hermano_id_str = user_id_str.replace("hermano_", "")
            from uuid import UUID
            try:
                hermano_id = UUID(hermano_id_str)
            except ValueError:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            result = await db.execute(
                select(Admin).where(Admin.hermano_id == hermano_id)
            )
            admin = result.scalar_one_or_none()
        else:
            # Regular user token - find admin by user_id
            from uuid import UUID
            try:
                user_id = UUID(user_id_str)
            except ValueError:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            result = await db.execute(
                select(Admin).where(Admin.user_id == user_id)
            )
            admin = result.scalar_one_or_none()
        
        if not admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return admin
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado. Por favor, inicie sesión nuevamente.")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido. Por favor, inicie sesión nuevamente.")
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Admin access required: {str(e)}")

class ApproveRequest(BaseModel):
    item_ids: List[str] = None  # If None, approve all
    action: str  # approve, reject, partial

@router.get("/requests")
async def get_all_requests(
    status: str = None,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all requests (admin only). Líderes de exhibidor solo ven solicitudes de sus exhibidores asignados.
    
    Si status='approved', muestra requests con items aprobados.
    Si status='cancelled', muestra requests con items cancelados/liberados.
    Si status=None, muestra todos los requests.
    """
    # Si es super_admin, puede ver todas las solicitudes
    # Si es lider_exhibidor, solo ve solicitudes de sus exhibidores asignados
    exhibitor_ids = None
    if admin.role == "lider_exhibidor":
        # Obtener exhibidores asignados a este líder
        leaders_result = await db.execute(
            select(ExhibitorLeader.exhibitor_id).where(ExhibitorLeader.admin_id == admin.id)
        )
        exhibitor_ids = [row[0] for row in leaders_result.all()]
        
        if not exhibitor_ids:
            # No tiene exhibidores asignados, retornar lista vacía
            return []
    
    # Construir query base con join de User para evitar N+1
    # NO filtrar por Request.status aquí, lo haremos después basado en items
    query = select(Request, User).join(User, Request.user_id == User.id)
    
    result = await db.execute(query.order_by(Request.created_at.desc()))
    requests_data = result.all()
    
    response = []
    for req, user in requests_data:
        
        # Get items with slot, schedule, and exhibitor information
        items_query = (
            select(RequestItem, Slot, Schedule, Exhibitor)
            .join(Slot, RequestItem.slot_id == Slot.id)
            .join(Schedule, Slot.schedule_id == Schedule.id)
            .join(Exhibitor, Slot.exhibitor_id == Exhibitor.id)
            .where(RequestItem.request_id == req.id)
        )
        
        # Si es lider_exhibidor, filtrar por exhibidores asignados
        if exhibitor_ids is not None:
            items_query = items_query.where(Exhibitor.id.in_(exhibitor_ids))
        
        # IMPORTANTE: Filtrar items por status si se especifica
        # Esto permite mostrar items liberados aunque el Request siga siendo "approved"
        if status:
            items_query = items_query.where(RequestItem.status == status)
            
            # Si es status='cancelled' (liberados), filtrar solo los del mes abierto del exhibidor
            if status == "cancelled":
                today = date.today()
                # Filtrar por slots cuya fecha esté dentro del rango abierto del exhibidor
                # Solo mostrar turnos liberados del mes que está actualmente abierto
                # Verificar que el exhibidor tenga fechas configuradas y esté abierto
                items_query = items_query.where(
                    Exhibitor.open_date.isnot(None),
                    Exhibitor.close_date.isnot(None),
                    Slot.slot_date >= Exhibitor.open_date,
                    Slot.slot_date <= Exhibitor.close_date,
                    Exhibitor.open_date <= today,
                    Exhibitor.close_date >= today
                )
        
        items_result = await db.execute(items_query)
        items_data = items_result.all()
        
        # Si es lider_exhibidor y no hay items después del filtro, saltar esta solicitud
        if exhibitor_ids is not None and not items_data:
            continue
        
        # Si hay filtro de status y no hay items que coincidan, saltar esta solicitud
        if status and not items_data:
            continue
        
        # Obtener todos los admins aprobadores en una sola query para evitar N+1
        approver_ids = [item.assigned_by for item, _, _, _ in items_data if item.assigned_by]
        approvers_map = {}
        if approver_ids:
            approvers_query = (
                select(Admin, User, Hermano)
                .outerjoin(User, Admin.user_id == User.id)
                .outerjoin(Hermano, Admin.hermano_id == Hermano.id)
                .where(Admin.id.in_(approver_ids))
            )
            approvers_result = await db.execute(approvers_query)
            for admin_obj, user_obj, hermano_obj in approvers_result.all():
                approver_name = None
                if user_obj:
                    approver_name = user_obj.full_name
                elif hermano_obj:
                    approver_name = hermano_obj.nombre
                approvers_map[admin_obj.id] = approver_name
        
        items = []
        for item, slot, schedule, exhibitor in items_data:
            # Obtener información del aprobador del mapa
            approver_name = approvers_map.get(item.assigned_by) if item.assigned_by else None
            
            items.append({
                "id": str(item.id),
                "status": item.status,
                "point": {
                    "id": str(exhibitor.id),
                    "name": exhibitor.name,
                    "code": exhibitor.code
                },
                "schedule": {
                    "id": str(schedule.id),
                    "start_time": str(schedule.start_time),
                    "end_time": str(schedule.end_time)
                },
                "date": slot.slot_date.isoformat() if slot.slot_date else None,
                "assigned_by": str(item.assigned_by) if item.assigned_by else None,
                "approver_name": approver_name
            })
        
        # Solo agregar request si tiene items después del filtro
        if items:
            response.append({
                "id": str(req.id),
                "user": {
                    "id": str(user.id),
                    "full_name": user.full_name,
                    "phone": user.phone
                },
                "status": req.status,
                "notes": req.notes,
                "created_at": req.created_at.isoformat(),
                "items_count": len(items),
                "items": items
            })
    
    return response

@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    data: ApproveRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Approve, reject or partially approve request. Si es lider_exhibidor, solo puede aprobar items de sus exhibidores."""
    result = await db.execute(
        select(Request).where(Request.id == UUID(request_id))
    )
    request = result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Si es lider_exhibidor, verificar que los items pertenezcan a sus exhibidores
    if admin.role == "lider_exhibidor":
        leaders_result = await db.execute(
            select(ExhibitorLeader.exhibitor_id).where(ExhibitorLeader.admin_id == admin.id)
        )
        exhibitor_ids = [row[0] for row in leaders_result.all()]
        
        if not exhibitor_ids:
            raise HTTPException(status_code=403, detail="No tiene exhibidores asignados")
        
        # Verificar que los items pertenezcan a sus exhibidores
        items_to_check = data.item_ids if data.item_ids else None
        if items_to_check:
            items_query = (
                select(RequestItem, Slot)
                .join(Slot, RequestItem.slot_id == Slot.id)
                .where(
                    RequestItem.request_id == request.id,
                    RequestItem.id.in_([UUID(id) for id in items_to_check])
                )
            )
        else:
            items_query = (
                select(RequestItem, Slot)
                .join(Slot, RequestItem.slot_id == Slot.id)
                .where(RequestItem.request_id == request.id)
            )
        
        items_with_slots = await db.execute(items_query)
        for item, slot in items_with_slots.all():
            if slot.exhibitor_id not in exhibitor_ids:
                raise HTTPException(
                    status_code=403, 
                    detail=f"No tiene permiso para aprobar items de este exhibidor"
                )
    
    # Get items
    items_result = await db.execute(
        select(RequestItem).where(RequestItem.request_id == request.id)
    )
    items = items_result.scalars().all()
    
    from datetime import datetime
    
    # Variable para guardar IDs de items liberados (para notificación masiva)
    liberated_item_ids = []
    
    if data.action == "approve":
        # Si se especifican item_ids, solo aprobar esos items
        if data.item_ids:
            approved_ids = [UUID(id) for id in data.item_ids]
            approved_count = 0
            for item in items:
                if item.id in approved_ids:
                    item.status = "approved"
                    item.assigned_by = admin.id
                    item.assigned_at = datetime.utcnow()
                    approved_count += 1
            # Actualizar estado de la solicitud
            if approved_count == len(items):
                request.status = "approved"
            elif approved_count > 0:
                request.status = "partial"
            else:
                request.status = "pending"
        else:
            # Aprobar todos los items
            request.status = "approved"
            for item in items:
                item.status = "approved"
                item.assigned_by = admin.id
                item.assigned_at = datetime.utcnow()
    elif data.action == "reject":
        # Si se especifican item_ids, solo cancelar/liberar esos items
        if data.item_ids:
            cancelled_ids = [UUID(id) for id in data.item_ids]
            cancelled_count = 0
            for item in items:
                if item.id in cancelled_ids:
                    item.status = "cancelled"  # Cambiar a cancelled en lugar de rejected
                    cancelled_count += 1
                    liberated_item_ids.append(str(item.id))  # Guardar para notificación
            # Actualizar estado de la solicitud
            if cancelled_count == len(items):
                request.status = "cancelled"
            elif cancelled_count > 0:
                # Verificar si hay items aprobados
                approved_count = sum(1 for item in items if item.status == "approved")
                request.status = "partial" if approved_count > 0 else "cancelled"
            else:
                request.status = "approved"  # Si no se cancela nada, queda aprobado
        else:
            # Cancelar todos los items
            request.status = "cancelled"
            for item in items:
                item.status = "cancelled"
                liberated_item_ids.append(str(item.id))  # Guardar para notificación
    elif data.action == "partial":
        if not data.item_ids:
            raise HTTPException(status_code=400, detail="item_ids required for partial approval")
        
        approved_ids = [UUID(id) for id in data.item_ids]
        approved_count = 0
        for item in items:
            if item.id in approved_ids:
                item.status = "approved"
                item.assigned_by = admin.id
                item.assigned_at = datetime.utcnow()
                approved_count += 1
            else:
                item.status = "cancelled"  # Cambiar a cancelled
        
        request.status = "partial" if approved_count > 0 else "cancelled"
    
    await db.commit()
    await db.refresh(request)
    
    # Log audit
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", f"request_{data.action}", {"request_id": str(request.id), "item_ids": data.item_ids})
    
    # Send notification
    send_notification_task.delay(str(request.id), f"request_{request.status}")
    
    # Si se liberaron turnos, notificar a todos los hermanos
    if data.action == "reject" and liberated_item_ids:
        for item_id in liberated_item_ids:
            # Enviar notificación masiva para cada turno liberado
            notify_slot_liberated_task.delay(item_id)
    
    return {"message": "Request updated", "status": request.status}


# Gestión de puntos de exhibidor (ahora usando Exhibitor directamente)
class ExhibitorCreate(BaseModel):
    code: str | None = None
    name: str
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    photo_url: str | None = None
    order: int = 1
    min_persons_per_slot: int = 3
    max_persons_per_slot: int = 5
    open_date: date | None = None
    close_date: date | None = None
    is_active: bool = True

class ExhibitorUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    photo_url: str | None = None
    order: int | None = None
    min_persons_per_slot: int | None = None
    max_persons_per_slot: int | None = None
    open_date: date | None = None
    close_date: date | None = None
    is_active: bool | None = None

class ScheduleCreate(BaseModel):
    weekday: int | None = None
    start_time: str  # Format: "HH:MM:SS"
    end_time: str    # Format: "HH:MM:SS"
    is_active: bool = True

class ScheduleUpdate(BaseModel):
    weekday: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_active: bool | None = None

@router.post("/points")
async def create_exhibitor(
    data: ExhibitorCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new exhibitor (punto de exhibidor)"""
    # Check if code already exists (if code is provided)
    if data.code:
        existing = await db.execute(select(Exhibitor).where(Exhibitor.code == data.code))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Exhibitor code already exists")
    
    exhibitor = Exhibitor(
        code=data.code,
        name=data.name,
        description=data.description,
        latitude=data.latitude,
        longitude=data.longitude,
        photo_url=data.photo_url,
        order=data.order,
        max_exhibidores=1,  # Siempre 1 exhibidor por punto
        min_persons_per_slot=data.min_persons_per_slot,
        max_persons_per_slot=data.max_persons_per_slot,
        open_date=data.open_date,
        close_date=data.close_date,
        is_active=data.is_active
    )
    db.add(exhibitor)
    await db.commit()
    await db.refresh(exhibitor)
    
    await log_audit(db, admin.user_id, "admin", "exhibitor_created", {"exhibitor_id": str(exhibitor.id)})
    
    return {
        "id": str(exhibitor.id),
        "code": exhibitor.code,
        "name": exhibitor.name,
        "description": exhibitor.description,
        "latitude": float(exhibitor.latitude) if exhibitor.latitude else None,
        "longitude": float(exhibitor.longitude) if exhibitor.longitude else None,
        "photo_url": exhibitor.photo_url,
        "order": exhibitor.order,
        "max_exhibidores": 1,
        "is_active": exhibitor.is_active
    }

@router.get("/points/{point_id}")
async def get_exhibitor(
    point_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get exhibitor (punto de exhibidor) by ID with schedules"""
    result = await db.execute(select(Exhibitor).where(Exhibitor.id == UUID(point_id)))
    exhibitor = result.scalar_one_or_none()
    
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    
    # Get schedules
    schedules_result = await db.execute(select(Schedule).where(Schedule.exhibitor_id == exhibitor.id))
    schedules = schedules_result.scalars().all()
    
    return {
        "id": str(exhibitor.id),
        "code": exhibitor.code,
        "name": exhibitor.name,
        "description": exhibitor.description,
        "latitude": float(exhibitor.latitude) if exhibitor.latitude else None,
        "longitude": float(exhibitor.longitude) if exhibitor.longitude else None,
        "photo_url": exhibitor.photo_url,
        "order": exhibitor.order,
        "max_exhibidores": 1,
        "is_active": exhibitor.is_active,
        "schedules": [
            {
                "id": str(s.id),
                "weekday": s.weekday,
                "start_time": str(s.start_time),
                "end_time": str(s.end_time),
                "is_active": s.is_active
            }
            for s in schedules
        ]
    }

@router.patch("/points/{point_id}")
async def update_exhibitor(
    point_id: str,
    data: ExhibitorUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update exhibitor (punto de exhibidor)"""
    result = await db.execute(select(Exhibitor).where(Exhibitor.id == UUID(point_id)))
    exhibitor = result.scalar_one_or_none()
    
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    
    if data.code is not None:
        # Check if code exists for another exhibitor
        existing = await db.execute(select(Exhibitor).where(Exhibitor.code == data.code, Exhibitor.id != UUID(point_id)))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Exhibitor code already exists")
        exhibitor.code = data.code
    
    if data.name is not None:
        exhibitor.name = data.name
    if data.description is not None:
        exhibitor.description = data.description
    if data.latitude is not None:
        exhibitor.latitude = data.latitude
    if data.longitude is not None:
        exhibitor.longitude = data.longitude
    if data.photo_url is not None:
        exhibitor.photo_url = data.photo_url
    if data.order is not None:
        exhibitor.order = data.order
    if data.is_active is not None:
        exhibitor.is_active = data.is_active
    if data.min_persons_per_slot is not None:
        exhibitor.min_persons_per_slot = data.min_persons_per_slot
    if data.max_persons_per_slot is not None:
        exhibitor.max_persons_per_slot = data.max_persons_per_slot
    if data.open_date is not None:
        exhibitor.open_date = data.open_date
    if data.close_date is not None:
        exhibitor.close_date = data.close_date
    
    await db.commit()
    await db.refresh(exhibitor)
    
    # Log audit
    await log_audit(db, admin.user_id, "admin", "exhibitor_updated", {"exhibitor_id": str(exhibitor.id)})
    
    return {
        "id": str(exhibitor.id),
        "code": exhibitor.code,
        "name": exhibitor.name,
        "description": exhibitor.description,
        "latitude": float(exhibitor.latitude) if exhibitor.latitude else None,
        "longitude": float(exhibitor.longitude) if exhibitor.longitude else None,
        "photo_url": exhibitor.photo_url,
        "order": exhibitor.order,
        "max_exhibidores": 1,
        "is_active": exhibitor.is_active
    }

@router.delete("/points/{point_id}")
async def delete_exhibitor(
    point_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete exhibitor (punto de exhibidor)"""
    result = await db.execute(select(Exhibitor).where(Exhibitor.id == UUID(point_id)))
    exhibitor = result.scalar_one_or_none()
    
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    
    await db.execute(delete(Exhibitor).where(Exhibitor.id == UUID(point_id)))
    await db.commit()
    await log_audit(db, admin.user_id, "admin", "exhibitor_deleted", {"exhibitor_id": str(point_id)})
    
    return {"message": "Exhibitor deleted"}


# Gestión de franjas horarias (schedules)
@router.post("/points/{point_id}/schedules")
async def create_schedule(
    point_id: str,
    data: ScheduleCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new schedule for an exhibitor (punto de exhibidor)"""
    # Verify exhibitor exists
    exhibitor_result = await db.execute(select(Exhibitor).where(Exhibitor.id == UUID(point_id)))
    exhibitor = exhibitor_result.scalar_one_or_none()
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    
    from datetime import time as dt_time
    try:
        start_time = dt_time.fromisoformat(data.start_time)
        end_time = dt_time.fromisoformat(data.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS")
    
    # Validar que las horas estén en punto (minutos = 0)
    if start_time.minute != 0:
        raise HTTPException(
            status_code=400, 
            detail=f"La hora de inicio debe estar en punto (minutos = 00). Se recibió {start_time.strftime('%H:%M')}. Use {start_time.hour:02d}:00"
        )
    if end_time.minute != 0:
        raise HTTPException(
            status_code=400, 
            detail=f"La hora de fin debe estar en punto (minutos = 00). Se recibió {end_time.strftime('%H:%M')}. Use {end_time.hour:02d}:00"
        )
    
    # Validar que end_time sea mayor que start_time
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="La hora de fin debe ser posterior a la hora de inicio")
    
    # Verificar solapamiento con horarios existentes del mismo exhibidor
    # Obtener todos los horarios del exhibidor que podrían solaparse
    existing_schedules_query = select(Schedule).where(
        Schedule.exhibitor_id == UUID(point_id),
        Schedule.is_active == True  # Solo verificar con horarios activos
    )
    
    # Si el nuevo horario tiene un weekday específico, solo verificar con horarios del mismo día o null
    # Si el nuevo horario tiene weekday null, verificar con todos los horarios
    if data.weekday is not None:
        existing_schedules_query = existing_schedules_query.where(
            (Schedule.weekday == data.weekday) | (Schedule.weekday.is_(None))
        )
    
    existing_schedules_result = await db.execute(existing_schedules_query)
    existing_schedules = existing_schedules_result.scalars().all()
    
    # Verificar solapamiento de horarios
    for existing in existing_schedules:
        # Si el horario existente tiene weekday null, se aplica a todos los días, incluyendo el del nuevo
        # Si el nuevo tiene weekday null, se aplica a todos los días, incluyendo el del existente
        # Si ambos tienen el mismo weekday, se solapan
        # Si uno tiene weekday y el otro null, se solapan (porque null aplica a todos los días)
        weekday_overlaps = (
            existing.weekday is None or  # Existente aplica a todos los días
            data.weekday is None or      # Nuevo aplica a todos los días
            existing.weekday == data.weekday  # Mismo día
        )
        
        if weekday_overlaps:
            # Verificar solapamiento de tiempos: dos rangos se solapan si start1 < end2 AND end1 > start2
            if start_time < existing.end_time and end_time > existing.start_time:
                # Mapear números de día a nombres
                weekday_names = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
                existing_weekday_str = "Todos los días" if existing.weekday is None else weekday_names.get(existing.weekday, f"Día {existing.weekday}")
                new_weekday_str = "Todos los días" if data.weekday is None else weekday_names.get(data.weekday, f"Día {data.weekday}")
                raise HTTPException(
                    status_code=400,
                    detail=f"El horario se solapa con uno existente: {existing.start_time.strftime('%H:%M')}-{existing.end_time.strftime('%H:%M')} ({existing_weekday_str}). "
                           f"El nuevo horario {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} ({new_weekday_str}) no puede solaparse con horarios existentes."
                )
    
    schedule = Schedule(
        exhibitor_id=UUID(point_id),
        weekday=data.weekday,
        start_time=start_time,
        end_time=end_time,
        is_active=data.is_active
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    
    await log_audit(db, admin.user_id, "admin", "schedule_created", {"schedule_id": str(schedule.id), "point_id": str(point_id)})
    
    return {
        "id": str(schedule.id),
        "weekday": schedule.weekday,
        "start_time": str(schedule.start_time),
        "end_time": str(schedule.end_time),
        "is_active": schedule.is_active
    }

@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update schedule"""
    result = await db.execute(select(Schedule).where(Schedule.id == UUID(schedule_id)))
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Preparar valores actualizados (usar los nuevos o mantener los existentes)
    from datetime import time as dt_time
    new_weekday = data.weekday if data.weekday is not None else schedule.weekday
    new_start_time = dt_time.fromisoformat(data.start_time) if data.start_time else schedule.start_time
    new_end_time = dt_time.fromisoformat(data.end_time) if data.end_time else schedule.end_time
    
    # Validar que las horas estén en punto (minutos = 0)
    if data.start_time and new_start_time.minute != 0:
        raise HTTPException(
            status_code=400, 
            detail=f"La hora de inicio debe estar en punto (minutos = 00). Se recibió {new_start_time.strftime('%H:%M')}. Use {new_start_time.hour:02d}:00"
        )
    if data.end_time and new_end_time.minute != 0:
        raise HTTPException(
            status_code=400, 
            detail=f"La hora de fin debe estar en punto (minutos = 00). Se recibió {new_end_time.strftime('%H:%M')}. Use {new_end_time.hour:02d}:00"
        )
    
    # Validar que end_time sea mayor que start_time
    if new_end_time <= new_start_time:
        raise HTTPException(status_code=400, detail="La hora de fin debe ser posterior a la hora de inicio")
    
    # Verificar solapamiento con otros horarios del mismo exhibidor (excluyendo el actual)
    existing_schedules_query = select(Schedule).where(
        Schedule.exhibitor_id == schedule.exhibitor_id,
        Schedule.id != UUID(schedule_id),  # Excluir el horario actual
        Schedule.is_active == True  # Solo verificar con horarios activos
    )
    
    # Si el horario actualizado tiene un weekday específico, solo verificar con horarios del mismo día o null
    if new_weekday is not None:
        existing_schedules_query = existing_schedules_query.where(
            (Schedule.weekday == new_weekday) | (Schedule.weekday.is_(None))
        )
    
    existing_schedules_result = await db.execute(existing_schedules_query)
    existing_schedules = existing_schedules_result.scalars().all()
    
    # Verificar solapamiento de horarios
    for existing in existing_schedules:
        weekday_overlaps = (
            existing.weekday is None or
            new_weekday is None or
            existing.weekday == new_weekday
        )
        
        if weekday_overlaps:
            # Verificar solapamiento de tiempos
            if new_start_time < existing.end_time and new_end_time > existing.start_time:
                # Mapear números de día a nombres
                weekday_names = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
                existing_weekday_str = "Todos los días" if existing.weekday is None else weekday_names.get(existing.weekday, f"Día {existing.weekday}")
                new_weekday_str = "Todos los días" if new_weekday is None else weekday_names.get(new_weekday, f"Día {new_weekday}")
                raise HTTPException(
                    status_code=400,
                    detail=f"El horario se solapa con uno existente: {existing.start_time.strftime('%H:%M')}-{existing.end_time.strftime('%H:%M')} ({existing_weekday_str}). "
                           f"El horario actualizado {new_start_time.strftime('%H:%M')}-{new_end_time.strftime('%H:%M')} ({new_weekday_str}) no puede solaparse con horarios existentes."
                )
    
    # Aplicar cambios
    if data.weekday is not None:
        schedule.weekday = data.weekday
    
    if data.start_time is not None:
        try:
            schedule.start_time = dt_time.fromisoformat(data.start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS")
    
    if data.end_time is not None:
        try:
            schedule.end_time = dt_time.fromisoformat(data.end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS")
    
    if data.is_active is not None:
        schedule.is_active = data.is_active
    
    await db.commit()
    await log_audit(db, admin.user_id, "admin", "schedule_updated", {"schedule_id": str(schedule_id), "is_active": schedule.is_active})
    
    return {
        "id": str(schedule.id),
        "weekday": schedule.weekday,
        "start_time": str(schedule.start_time),
        "end_time": str(schedule.end_time),
        "is_active": schedule.is_active
    }

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete schedule"""
    result = await db.execute(select(Schedule).where(Schedule.id == UUID(schedule_id)))
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    await db.execute(delete(Schedule).where(Schedule.id == UUID(schedule_id)))
    await db.commit()
    await log_audit(db, admin.user_id, "admin", "schedule_deleted", {"schedule_id": str(schedule_id)})
    
    return {"message": "Schedule deleted"}


# Gestión de usuarios
class UserCreate(BaseModel):
    full_name: str
    phone: str
    email: str | None = None
    is_active: bool = True

class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None

@router.get("/users")
async def get_all_users(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all users (hermanos) - includes all users from CSV, marks which are admins"""
    # Get all users - ALL users including those who are admins
    result = await db.execute(select(User).order_by(User.full_name))
    users = result.scalars().all()
    
    # Get all admin user_ids to mark them (but don't exclude them)
    admin_result = await db.execute(select(Admin.user_id))
    admin_user_ids = {str(uid) for uid, in admin_result.all()}
    
    return [
        {
            "id": str(u.id),
            "full_name": u.full_name,
            "phone": u.phone,
            "email": u.email,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
            "is_admin": str(u.id) in admin_user_ids
        }
        for u in users
    ]

@router.post("/users")
async def create_user(
    data: UserCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new user"""
    # Check if phone already exists
    existing = await db.execute(select(User).where(User.phone == data.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Phone already exists")
    
    user = User(
        full_name=data.full_name,
        phone=data.phone,
        email=data.email,
        is_active=data.is_active
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    await log_audit(db, admin.user_id, "admin", "user_created", {"user_id": str(user.id)})
    
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "phone": user.phone,
        "email": user.email,
        "is_active": user.is_active
    }

@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user"""
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        # Check if phone already exists for another user
        existing = await db.execute(select(User).where(User.phone == data.phone, User.id != UUID(user_id)))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Phone already exists")
        user.phone = data.phone
    if data.email is not None:
        user.email = data.email
    if data.is_active is not None:
        user.is_active = data.is_active
    
    await db.commit()
    await log_audit(db, admin.user_id, "admin", "user_updated", {"user_id": str(user.id)})
    
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "phone": user.phone,
        "email": user.email,
        "is_active": user.is_active
    }

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete user"""
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.execute(delete(User).where(User.id == UUID(user_id)))
    await db.commit()
    await log_audit(db, admin.user_id, "admin", "user_deleted", {"user_id": str(user_id)})
    
    return {"message": "User deleted"}


# Gestión de hermanos
class HermanoCreate(BaseModel):
    nombre: str
    congregacion: str | None = None
    telefono: str
    genero: str = "hermano"  # 'hermano' or 'hermana'
    is_active: bool = True

class HermanoUpdate(BaseModel):
    nombre: str | None = None
    congregacion: str | None = None
    telefono: str | None = None
    genero: str | None = None
    is_active: bool | None = None

@router.get("/hermanos")
async def get_all_hermanos(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all hermanos - includes all from CSV, marks which are admins"""
    result = await db.execute(select(Hermano).order_by(Hermano.nombre))
    hermanos = result.scalars().all()
    
    # Get all admin hermano_ids to mark them
    admin_result = await db.execute(select(Admin.hermano_id).where(Admin.hermano_id.isnot(None)))
    admin_hermano_ids = {str(hid) for hid, in admin_result.all()}
    
    return [
        {
            "id": str(h.id),
            "nombre": h.nombre,
            "congregacion": h.congregacion,
            "telefono": h.telefono,
            "genero": h.genero or detect_gender_from_name(h.nombre),
            "gender_label": get_gender_label(h.nombre) if not h.genero else ("Hermana" if h.genero == "hermana" else "Hermano"),
            "is_active": h.is_active,
            "created_at": h.created_at.isoformat(),
            "is_admin": str(h.id) in admin_hermano_ids
        }
        for h in hermanos
    ]

@router.post("/hermanos")
async def create_hermano(
    data: HermanoCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new hermano"""
    # Check if telefono already exists
    existing = await db.execute(select(Hermano).where(Hermano.telefono == data.telefono))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Teléfono ya existe")
    
    hermano = Hermano(
        nombre=data.nombre,
        congregacion=data.congregacion,
        telefono=data.telefono,
        genero=data.genero,
        is_active=data.is_active
    )
    db.add(hermano)
    await db.commit()
    await db.refresh(hermano)
    
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "hermano_created", {"hermano_id": str(hermano.id)})
    
    return {
        "id": str(hermano.id),
        "nombre": hermano.nombre,
        "congregacion": hermano.congregacion,
        "telefono": hermano.telefono,
        "genero": hermano.genero or "hermano",
        "gender_label": "Hermana" if hermano.genero == "hermana" else "Hermano",
        "is_active": hermano.is_active
    }

@router.patch("/hermanos/{hermano_id}")
async def update_hermano(
    hermano_id: str,
    data: HermanoUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update hermano"""
    result = await db.execute(select(Hermano).where(Hermano.id == UUID(hermano_id)))
    hermano = result.scalar_one_or_none()
    
    if not hermano:
        raise HTTPException(status_code=404, detail="Hermano no encontrado")
    
    if data.nombre is not None:
        hermano.nombre = data.nombre
    if data.congregacion is not None:
        hermano.congregacion = data.congregacion
    if data.telefono is not None:
        # Check if telefono already exists for another hermano
        existing = await db.execute(select(Hermano).where(Hermano.telefono == data.telefono, Hermano.id != UUID(hermano_id)))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Teléfono ya existe")
        hermano.telefono = data.telefono
    if data.genero is not None:
        hermano.genero = data.genero
    if data.is_active is not None:
        hermano.is_active = data.is_active
    
    await db.commit()
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "hermano_updated", {"hermano_id": str(hermano.id)})
    
    return {
        "id": str(hermano.id),
        "nombre": hermano.nombre,
        "congregacion": hermano.congregacion,
        "telefono": hermano.telefono,
        "genero": hermano.genero or "hermano",
        "gender_label": "Hermana" if hermano.genero == "hermana" else "Hermano",
        "is_active": hermano.is_active
    }

@router.delete("/hermanos/{hermano_id}")
async def delete_hermano(
    hermano_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete hermano"""
    result = await db.execute(select(Hermano).where(Hermano.id == UUID(hermano_id)))
    hermano = result.scalar_one_or_none()
    
    if not hermano:
        raise HTTPException(status_code=404, detail="Hermano no encontrado")
    
    await db.execute(delete(Hermano).where(Hermano.id == UUID(hermano_id)))
    await db.commit()
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "hermano_deleted", {"hermano_id": str(hermano_id)})
    
    return {"message": "Hermano eliminado"}


# Gestión de administradores
class AdminCreate(BaseModel):
    user_id: str | None = None
    hermano_id: str | None = None
    username: str
    password: str
    # Roles soportados:
    # - super_admin: administra toda la plataforma
    # - lider_exhibidor: líder de uno o más puntos de exhibidor
    role: str = "lider_exhibidor"

class AdminUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None

@router.get("/admins")
async def get_all_admins(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all admins (admin only) - supports both user_id and hermano_id"""
    # Get admins with user relationship
    result_user = await db.execute(
        select(Admin, User)
        .join(User, Admin.user_id == User.id)
        .where(Admin.user_id.isnot(None))
        .order_by(User.full_name)
    )
    admins_with_users = result_user.all()
    
    # Get admins with hermano relationship
    result_hermano = await db.execute(
        select(Admin, Hermano)
        .join(Hermano, Admin.hermano_id == Hermano.id)
        .where(Admin.hermano_id.isnot(None))
        .order_by(Hermano.nombre)
    )
    admins_with_hermanos = result_hermano.all()
    
    response = []
    
    # Helper para obtener roles de exhibidor (puntos) por admin
    async def get_exhibitor_roles_for_admin(admin_id: UUID):
        from app.models import ExhibitorLeader, Exhibitor  # Import local para evitar ciclos
        roles_result = await db.execute(
            select(ExhibitorLeader, Exhibitor)
            .join(Exhibitor, ExhibitorLeader.exhibitor_id == Exhibitor.id)
            .where(ExhibitorLeader.admin_id == admin_id)
        )
        roles = []
        for el, ex in roles_result.all():
            roles.append({
                "exhibitor_id": str(ex.id),
                "exhibitor_name": ex.name,
                "position": el.position,
            })
        return roles
    
    # Add admins with users
    for a, u in admins_with_users:
        exhibitor_roles = await get_exhibitor_roles_for_admin(a.id)
        response.append({
            "id": str(a.id),
            "user_id": str(a.user_id) if a.user_id else None,
            "hermano_id": str(a.hermano_id) if a.hermano_id else None,
            "username": a.username,
            "role": a.role,
            "user": {
                "id": str(u.id),
                "full_name": u.full_name,
                "phone": u.phone,
                "email": u.email,
                "is_active": u.is_active
            },
            "hermano": None,
            "created_at": a.created_at.isoformat(),
            "exhibitor_roles": exhibitor_roles,
        })
    
    # Add admins with hermanos
    for a, h in admins_with_hermanos:
        exhibitor_roles = await get_exhibitor_roles_for_admin(a.id)
        response.append({
            "id": str(a.id),
            "user_id": str(a.user_id) if a.user_id else None,
            "hermano_id": str(a.hermano_id) if a.hermano_id else None,
            "username": a.username,
            "role": a.role,
            "user": None,
            "hermano": {
                "id": str(h.id),
                "nombre": h.nombre,
                "congregacion": h.congregacion,
                "telefono": h.telefono,
                "is_active": h.is_active
            },
            "created_at": a.created_at.isoformat(),
            "exhibitor_roles": exhibitor_roles,
        })
    
    return response

@router.post("/admins")
async def create_admin(
    data: AdminCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new admin - can use user_id or hermano_id"""
    if not data.user_id and not data.hermano_id:
        raise HTTPException(status_code=400, detail="Debe proporcionar user_id o hermano_id")
    
    if data.user_id and data.hermano_id:
        raise HTTPException(status_code=400, detail="Solo puede proporcionar user_id o hermano_id, no ambos")
    
    # Check if user or hermano exists
    if data.user_id:
        user_result = await db.execute(select(User).where(User.id == UUID(data.user_id)))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Check if user already has admin
        existing_admin = await db.execute(select(Admin).where(Admin.user_id == UUID(data.user_id)))
        if existing_admin.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="El usuario ya tiene cuenta de administrador")
    
    if data.hermano_id:
        hermano_result = await db.execute(select(Hermano).where(Hermano.id == UUID(data.hermano_id)))
        hermano = hermano_result.scalar_one_or_none()
        if not hermano:
            raise HTTPException(status_code=404, detail="Hermano no encontrado")
        
        # Check if hermano already has admin
        existing_admin = await db.execute(select(Admin).where(Admin.hermano_id == UUID(data.hermano_id)))
        if existing_admin.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="El hermano ya tiene cuenta de administrador")
    
    # Check if username exists
    existing_username = await db.execute(select(Admin).where(Admin.username == data.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    
    new_admin = Admin(
        user_id=UUID(data.user_id) if data.user_id else None,
        hermano_id=UUID(data.hermano_id) if data.hermano_id else None,
        username=data.username,
        password_hash=pwd_context.hash(data.password),
        role=data.role
    )
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "admin_created", {"admin_id": str(new_admin.id)})
    
    return {
        "id": str(new_admin.id),
        "user_id": str(new_admin.user_id),
        "username": new_admin.username,
        "role": new_admin.role,
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone": user.phone
        }
    }

@router.patch("/admins/{admin_id}")
async def update_admin(
    admin_id: str,
    data: AdminUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update admin"""
    result = await db.execute(select(Admin).where(Admin.id == UUID(admin_id)))
    admin_obj = result.scalar_one_or_none()
    
    if not admin_obj:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    if data.username is not None:
        # Check if username exists for another admin
        existing = await db.execute(select(Admin).where(Admin.username == data.username, Admin.id != UUID(admin_id)))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already exists")
        admin_obj.username = data.username
    
    if data.password is not None:
        admin_obj.password_hash = pwd_context.hash(data.password)
    
    if data.role is not None:
        admin_obj.role = data.role
    
    await db.commit()
    await log_audit(db, admin.user_id, "admin", "admin_updated", {"admin_id": str(admin_id)})
    
    # Get user data
    user_result = await db.execute(select(User).where(User.id == admin_obj.user_id))
    user = user_result.scalar_one()
    
    return {
        "id": str(admin_obj.id),
        "user_id": str(admin_obj.user_id),
        "username": admin_obj.username,
        "role": admin_obj.role,
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone": user.phone
        }
    }

@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete admin"""
    result = await db.execute(select(Admin).where(Admin.id == UUID(admin_id)))
    admin_obj = result.scalar_one_or_none()
    
    if not admin_obj:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    await db.execute(delete(Admin).where(Admin.id == UUID(admin_id)))
    await db.commit()
    await log_audit(db, admin.user_id, "admin", "admin_deleted", {"admin_id": str(admin_id)})
    
    return {"message": "Admin deleted"}


# Gestión de horarios (schedules)
@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    is_active: bool = None,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update schedule status"""
    result = await db.execute(select(Schedule).where(Schedule.id == UUID(schedule_id)))
    schedule = result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if is_active is not None:
        schedule.is_active = is_active
    
    await db.commit()
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "schedule_updated", {"schedule_id": str(schedule_id), "is_active": is_active})
    
    return {"message": "Schedule updated", "schedule": {"id": str(schedule.id), "is_active": schedule.is_active}}


# Gestión de líderes de exhibidor
class ExhibitorLeaderCreate(BaseModel):
    admin_id: str
    exhibitor_id: str
    position: str  # 'principal' or 'suplente'

class ExhibitorLeaderUpdate(BaseModel):
    admin_id: str | None = None
    position: str | None = None

@router.get("/exhibitor-leaders")
async def get_exhibitor_leaders(
    exhibitor_id: str = None,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all exhibitor leaders. Si se proporciona exhibitor_id, solo retorna líderes de ese exhibidor."""
    query = select(ExhibitorLeader, Admin, Exhibitor)
    if exhibitor_id:
        query = query.where(ExhibitorLeader.exhibitor_id == UUID(exhibitor_id))
    
    query = query.join(Admin, ExhibitorLeader.admin_id == Admin.id)
    query = query.join(Exhibitor, ExhibitorLeader.exhibitor_id == Exhibitor.id)
    
    result = await db.execute(query.order_by(ExhibitorLeader.position, Exhibitor.name))
    leaders_data = result.all()
    
    response = []
    for leader, admin_obj, exhibitor in leaders_data:
        # Obtener nombre del admin
        admin_name = None
        if admin_obj.user_id:
            user_result = await db.execute(select(User).where(User.id == admin_obj.user_id))
            user = user_result.scalar_one_or_none()
            admin_name = user.full_name if user else None
        elif admin_obj.hermano_id:
            hermano_result = await db.execute(select(Hermano).where(Hermano.id == admin_obj.hermano_id))
            hermano = hermano_result.scalar_one_or_none()
            admin_name = hermano.nombre if hermano else None
        
        response.append({
            "id": str(leader.id),
            "admin_id": str(leader.admin_id),
            "admin_name": admin_name,
            "admin_username": admin_obj.username,
            "exhibitor_id": str(leader.exhibitor_id),
            "exhibitor_name": exhibitor.name,
            "position": leader.position,
            "created_at": leader.created_at.isoformat()
        })
    
    return response

@router.post("/exhibitor-leaders")
async def create_exhibitor_leader(
    data: ExhibitorLeaderCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new exhibitor leader. Solo super_admin puede crear líderes."""
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Solo super administradores pueden gestionar líderes")
    
    # Verificar que el admin existe y es lider_exhibidor
    admin_result = await db.execute(select(Admin).where(Admin.id == UUID(data.admin_id)))
    admin_obj = admin_result.scalar_one_or_none()
    if not admin_obj:
        raise HTTPException(status_code=404, detail="Admin no encontrado")
    
    if admin_obj.role != "lider_exhibidor":
        raise HTTPException(status_code=400, detail="El admin debe tener rol 'lider_exhibidor'")
    
    # Verificar que el exhibitor existe
    exhibitor_result = await db.execute(select(Exhibitor).where(Exhibitor.id == UUID(data.exhibitor_id)))
    exhibitor = exhibitor_result.scalar_one_or_none()
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor no encontrado")
    
    # Validar posición
    valid_positions = ["principal", "suplente", "encargado_turnos_principal", "encargado_turnos_remplazo", "publicaciones_mantenimiento"]
    if data.position not in valid_positions:
        raise HTTPException(status_code=400, detail=f"Position debe ser uno de: {', '.join(valid_positions)}")
    
    # Verificar que no haya ya un líder con la misma posición para este exhibidor
    # Solo las posiciones únicas deben validarse (encargado_turnos_principal es único, los demás pueden repetirse)
    unique_positions = ["principal", "encargado_turnos_principal"]
    if data.position in unique_positions:
        existing_leader = await db.execute(
            select(ExhibitorLeader).where(
                ExhibitorLeader.exhibitor_id == UUID(data.exhibitor_id),
                ExhibitorLeader.position == data.position
            )
        )
        if existing_leader.scalar_one_or_none():
            position_labels = {
                "principal": "líder principal",
                "encargado_turnos_principal": "Encargado de Turnos Principal"
            }
            label = position_labels.get(data.position, data.position)
            raise HTTPException(status_code=400, detail=f"Ya existe un {label} para este exhibidor")
    
    # Verificar que el mismo admin no tenga la misma posición en el mismo exhibidor
    existing = await db.execute(
        select(ExhibitorLeader).where(
            ExhibitorLeader.admin_id == UUID(data.admin_id),
            ExhibitorLeader.exhibitor_id == UUID(data.exhibitor_id),
            ExhibitorLeader.position == data.position
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Este admin ya tiene esta posición asignada en este exhibidor")
    
    # Verificar límite: un líder puede tener máximo 2 exhibidores
    count_result = await db.execute(
        select(func.count(ExhibitorLeader.id)).where(ExhibitorLeader.admin_id == UUID(data.admin_id))
    )
    current_count = count_result.scalar() or 0
    if current_count >= 2:
        raise HTTPException(status_code=400, detail="Un líder de exhibidor puede tener máximo 2 exhibidores asignados")
    
    leader = ExhibitorLeader(
        admin_id=UUID(data.admin_id),
        exhibitor_id=UUID(data.exhibitor_id),
        position=data.position
    )
    db.add(leader)
    await db.commit()
    await db.refresh(leader)
    
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "exhibitor_leader_created", {
        "leader_id": str(leader.id),
        "admin_id": data.admin_id,
        "exhibitor_id": data.exhibitor_id
    })
    
    return {
        "id": str(leader.id),
        "admin_id": str(leader.admin_id),
        "exhibitor_id": str(leader.exhibitor_id),
        "position": leader.position
    }

@router.patch("/exhibitor-leaders/{leader_id}")
async def update_exhibitor_leader(
    leader_id: str,
    data: ExhibitorLeaderUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update exhibitor leader. Solo super_admin puede actualizar."""
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Solo super administradores pueden gestionar líderes")
    
    result = await db.execute(select(ExhibitorLeader).where(ExhibitorLeader.id == UUID(leader_id)))
    leader = result.scalar_one_or_none()
    
    if not leader:
        raise HTTPException(status_code=404, detail="Líder no encontrado")
    
    if data.admin_id is not None:
        # Verificar que el nuevo admin existe y es lider_exhibidor
        admin_result = await db.execute(select(Admin).where(Admin.id == UUID(data.admin_id)))
        admin_obj = admin_result.scalar_one_or_none()
        if not admin_obj:
            raise HTTPException(status_code=404, detail="Admin no encontrado")
        
        if admin_obj.role != "lider_exhibidor":
            raise HTTPException(status_code=400, detail="El admin debe tener rol 'lider_exhibidor'")
        
        # Verificar límite de 2 exhibidores para el nuevo admin
        count_result = await db.execute(
            select(func.count(ExhibitorLeader.id)).where(
                ExhibitorLeader.admin_id == UUID(data.admin_id),
                ExhibitorLeader.id != UUID(leader_id)
            )
        )
        current_count = count_result.scalar() or 0
        if current_count >= 2:
            raise HTTPException(status_code=400, detail="El nuevo admin ya tiene 2 exhibidores asignados")
        
        leader.admin_id = UUID(data.admin_id)
    
    if data.position is not None:
        valid_positions = ["principal", "suplente", "encargado_turnos_principal", "encargado_turnos_remplazo", "publicaciones_mantenimiento"]
        if data.position not in valid_positions:
            raise HTTPException(status_code=400, detail=f"Position debe ser uno de: {', '.join(valid_positions)}")
        
        # Si se cambia a principal, verificar que no haya otro principal
        if data.position == "principal":
            existing_principal = await db.execute(
                select(ExhibitorLeader).where(
                    ExhibitorLeader.exhibitor_id == leader.exhibitor_id,
                    ExhibitorLeader.position == "principal",
                    ExhibitorLeader.id != UUID(leader_id)
                )
            )
            if existing_principal.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Ya existe un líder principal para este exhibidor")
        
        leader.position = data.position
    
    await db.commit()
    await db.refresh(leader)
    
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "exhibitor_leader_updated", {"leader_id": str(leader_id)})
    
    return {
        "id": str(leader.id),
        "admin_id": str(leader.admin_id),
        "exhibitor_id": str(leader.exhibitor_id),
        "position": leader.position
    }

@router.delete("/exhibitor-leaders/{leader_id}")
async def delete_exhibitor_leader(
    leader_id: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete exhibitor leader. Solo super_admin puede eliminar."""
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Solo super administradores pueden gestionar líderes")
    
    result = await db.execute(select(ExhibitorLeader).where(ExhibitorLeader.id == UUID(leader_id)))
    leader = result.scalar_one_or_none()
    
    if not leader:
        raise HTTPException(status_code=404, detail="Líder no encontrado")
    
    await db.execute(delete(ExhibitorLeader).where(ExhibitorLeader.id == UUID(leader_id)))
    await db.commit()
    
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "exhibitor_leader_deleted", {"leader_id": str(leader_id)})
    
    return {"message": "Líder eliminado"}
