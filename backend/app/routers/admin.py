from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, Date, cast
from typing import List
from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
import re

from app.database import get_db
from app.models import Request, RequestItem, User, Admin, Exhibitor, Schedule, Hermano, Slot, ExhibitorLeader
from app.utils.gender_detector import detect_gender_from_name, get_gender_label
from app.utils.security import get_current_user
from app.utils.audit import log_audit
from app.scheduler import send_notification, notify_slot_liberated
from app.routers.requests import check_time_conflict
from passlib.context import CryptContext
import asyncio

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
    from sqlalchemy import text

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

        # Use raw SQL to find admin (avoiding SQLAlchemy ORM issues with SQLite)
        if user_id_str.startswith("hermano_"):
            hermano_id_str = user_id_str.replace("hermano_", "")
            from uuid import UUID
            try:
                hermano_id = str(UUID(hermano_id_str))
            except ValueError:
                raise HTTPException(status_code=403, detail="Admin access required")

            # Use raw SQL
            result = await db.execute(text(f"SELECT id, username, user_id, hermano_id, password_hash, role FROM admins WHERE hermano_id = '{hermano_id}'"))
            admin_row = result.fetchone()
            if admin_row:
                # Create a mock Admin object with the raw data
                from app.models import Admin as AdminModel
                admin = AdminModel(
                    id=admin_row[0],
                    username=admin_row[1],
                    user_id=admin_row[2],
                    hermano_id=admin_row[3],
                    password_hash=admin_row[4],
                    role=admin_row[5]
                )
            else:
                admin = None
        else:
            # Regular user token - find admin by user_id
            from uuid import UUID
            try:
                user_id = str(UUID(user_id_str))
            except ValueError:
                raise HTTPException(status_code=403, detail="Admin access required")

            # Use raw SQL
            result = await db.execute(text(f"SELECT id, username, user_id, hermano_id, password_hash, role FROM admins WHERE user_id = '{user_id}'"))
            admin_row = result.fetchone()
            if admin_row:
                # Create a mock Admin object with the raw data
                from app.models import Admin as AdminModel
                admin = AdminModel(
                    id=admin_row[0],
                    username=admin_row[1],
                    user_id=admin_row[2],
                    hermano_id=admin_row[3],
                    password_hash=admin_row[4],
                    role=admin_row[5]
                )
            else:
                admin = None

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
    current_month_only: bool = True,  # Por defecto, solo mostrar mes actual
    year: int = None,  # Permite filtrar por año específico
    month: int = None,  # Permite filtrar por mes específico
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all requests (admin only). Líderes de exhibidor solo ven solicitudes de sus exhibidores asignados.
    
    Si status='approved', muestra requests con items aprobados.
    Si status='cancelled', muestra requests con items cancelados/liberados.
    Si status=None, muestra todos los requests.
    
    Por defecto (current_month_only=True), solo muestra turnos del mes actual.
    Use current_month_only=False para ver todos los turnos históricos.
    """
    from datetime import date as date_type
    import calendar as cal_module
    # Si es super_admin, puede ver todas las solicitudes
    # Si es encargado, solo ve solicitudes de sus exhibidores asignados
    exhibitor_ids = None
    if admin.role in ("encargado", "lider_exhibidor"):
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
        
        # Filtro por mes actual (por defecto) o mes específico
        if current_month_only:
            today = date_type.today()
            target_year = year or today.year
            target_month = month or today.month
            
            # Calcular primer y último día del mes
            first_day = date_type(target_year, target_month, 1)
            last_day = date_type(target_year, target_month, cal_module.monthrange(target_year, target_month)[1])
            
            # Aplicar filtro de fecha
            items_query = items_query.where(
                Slot.slot_date >= first_day,
                Slot.slot_date <= last_day
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
    
    # Si es encargado, verificar que los items pertenezcan a sus exhibidores
    if admin.role in ("encargado", "lider_exhibidor"):
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
    
    # ── VALIDAR SOLAPAMIENTO DE HORARIOS ANTES DE APROBAR ─────────────────
    # Si se está aprobando (total o parcial), verificar que no haya conflictos de horario
    if data.action in ("approve", "partial"):
        # Determinar qué items se van a aprobar
        items_to_approve = []
        if data.item_ids:
            approved_ids = [UUID(id) for id in data.item_ids]
            for item in items:
                if item.id in approved_ids:
                    items_to_approve.append(item)
        else:
            # Se aprueban todos los items que no estén ya aprobados
            for item in items:
                if item.status != "approved":
                    items_to_approve.append(item)
        
        # Para cada item que se va a aprobar, verificar solapamiento
        conflicts = []
        for item in items_to_approve:
            # Obtener información del slot, schedule y exhibidor
            item_info_result = await db.execute(
                select(RequestItem, Slot, Schedule, Exhibitor)
                .join(Slot, RequestItem.slot_id == Slot.id)
                .join(Schedule, Slot.schedule_id == Schedule.id)
                .join(Exhibitor, Slot.exhibitor_id == Exhibitor.id)
                .where(RequestItem.id == item.id)
            )
            item_info = item_info_result.first()
            
            if not item_info:
                continue
            
            _, slot, schedule, exhibitor = item_info
            
            # Verificar solapamiento con otros turnos del usuario
            conflict_check = await check_time_conflict(
                db=db,
                user_id=request.user_id,
                slot_date=slot.slot_date,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                exclude_request_id=str(request.id)
            )
            
            if conflict_check['has_conflict']:
                conflicts.append({
                    "item_id": str(item.id),
                    "exhibidor": exhibitor.name,
                    "fecha": slot.slot_date.isoformat(),
                    "hora_inicio": str(schedule.start_time)[:5],
                    "hora_fin": str(schedule.end_time)[:5],
                    "message": conflict_check['conflict_info']['message']
                })
        
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "No se puede aprobar la solicitud debido a conflictos de horario",
                    "conflicts": conflicts,
                    "error_code": "TIME_CONFLICT"
                }
            )
    # ────────────────────────────────────────────────────────────────────────
    
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
    asyncio.create_task(send_notification(str(request.id), f"request_{request.status}"))

    # Si se liberaron turnos, notificar a todos los hermanos
    if data.action == "reject" and liberated_item_ids:
        for item_id in liberated_item_ids:
            # Enviar notificación masiva para cada turno liberado
            asyncio.create_task(notify_slot_liberated(item_id))
    
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
    type: str  # all_days, weekends, specific_day
    weekday: int | None = None  # 0-6 for specific_day, NULL for all_days, 5&6 for weekends
    start_time: str  # Format: "HH:MM:SS"
    end_time: str    # Format: "HH:MM:SS"
    is_active: bool = True

class ScheduleUpdate(BaseModel):
    type: str | None = None
    weekday: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    is_active: bool | None = None

@router.get("/exhibitors")
async def list_exhibitors(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    active_only: bool = False,
    include_all_schedules: bool = False
):
    """List all exhibitors"""
    query = select(Exhibitor)
    if active_only:
        query = query.where(Exhibitor.is_active == True)
    query = query.order_by(Exhibitor.code)

    result = await db.execute(query)
    exhibitors = result.scalars().all()

    return [
        {
            "id": str(e.id),
            "code": e.code,
            "name": e.name,
            "description": e.description,
            "latitude": float(e.latitude) if e.latitude else None,
            "longitude": float(e.longitude) if e.longitude else None,
            "photo_url": e.photo_url,
            "is_active": e.is_active,
            "max_exhibidores": e.max_exhibidores,
            "min_persons_per_slot": e.min_persons_per_slot,
            "max_persons_per_slot": e.max_persons_per_slot,
        }
        for e in exhibitors
    ]

@router.get("/points")
async def list_points(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    active_only: bool = False,
    include_all_schedules: bool = False
):
    """List all points (alias for exhibitors)"""
    query = select(Exhibitor)
    if active_only:
        query = query.where(Exhibitor.is_active == True)
    query = query.order_by(Exhibitor.code)

    result = await db.execute(query)
    exhibitors = result.scalars().all()

    response = []
    for e in exhibitors:
        try:
            # Get schedules for this exhibitor
            schedules_result = await db.execute(
                select(Schedule).where(Schedule.exhibitor_id == e.id).order_by(Schedule.id)
            )
            schedules = schedules_result.scalars().all() or []

            # Get leaders for this exhibitor
            leaders_result = await db.execute(
                select(ExhibitorLeader).where(ExhibitorLeader.exhibitor_id == e.id)
            )
            leaders = leaders_result.scalars().all() or []
        except Exception as err:
            schedules = []
            leaders = []

        response.append({
            "id": str(e.id),
            "code": e.code,
            "name": e.name,
            "description": e.description,
            "latitude": float(e.latitude) if e.latitude else None,
            "longitude": float(e.longitude) if e.longitude else None,
            "photo_url": e.photo_url,
            "is_active": e.is_active,
            "max_exhibidores": e.max_exhibidores,
            "min_persons_per_slot": e.min_persons_per_slot,
            "max_persons_per_slot": e.max_persons_per_slot,
            "schedules": [
                {
                    "id": str(s.id),
                    "exhibitor_id": str(s.exhibitor_id),
                    "type": s.type,
                    "weekday": s.weekday,
                    "start_time": str(s.start_time) if s.start_time else None,
                    "end_time": str(s.end_time) if s.end_time else None,
                    "is_active": s.is_active,
                }
                for s in schedules
            ] if schedules else [],
            "leaders": [
                {
                    "id": str(l.id),
                    "exhibitor_id": str(l.exhibitor_id),
                    "admin_id": str(l.admin_id) if l.admin_id else None,
                    "position": l.position,
                }
                for l in leaders
            ] if leaders else [],
        })

    return response

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
    
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "exhibitor_created", {"exhibitor_id": str(exhibitor.id)})
    
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
    from sqlalchemy import text

    # Use raw SQL to fetch exhibitor (SQLite async issues with ORM)
    result = await db.execute(text(f"SELECT id, code, name, description, latitude, longitude, photo_url, \"order\", is_active FROM exhibitors WHERE id = '{point_id}'"))
    exhibitor_row = result.fetchone()

    if not exhibitor_row:
        raise HTTPException(status_code=404, detail="Exhibitor not found")

    exhibitor_id = exhibitor_row[0]

    # Get schedules
    schedules_result = await db.execute(text(f"SELECT id, type, weekday, start_time, end_time, is_active FROM schedules WHERE exhibitor_id = '{exhibitor_id}'"))
    schedules_rows = schedules_result.fetchall()

    return {
        "id": str(exhibitor_row[0]),
        "code": exhibitor_row[1],
        "name": exhibitor_row[2],
        "description": exhibitor_row[3],
        "latitude": float(exhibitor_row[4]) if exhibitor_row[4] else None,
        "longitude": float(exhibitor_row[5]) if exhibitor_row[5] else None,
        "photo_url": exhibitor_row[6],
        "order": exhibitor_row[7],
        "max_exhibidores": 1,
        "is_active": exhibitor_row[8],
        "schedules": [
            {
                "id": str(s[0]),
                "type": s[1],
                "weekday": s[2],
                "start_time": str(s[3]),
                "end_time": str(s[4]),
                "is_active": s[5]
            }
            for s in schedules_rows
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
    from sqlalchemy import text

    # Use raw SQL to fetch exhibitor (SQLite async issues with ORM)
    result = await db.execute(text(f"SELECT id, code, name, description, latitude, longitude, photo_url, \"order\", is_active, min_persons_per_slot, max_persons_per_slot, open_date, close_date FROM exhibitors WHERE id = '{point_id}'"))
    exhibitor_row = result.fetchone()

    if not exhibitor_row:
        raise HTTPException(status_code=404, detail="Exhibitor not found")

    # Create exhibitor object from raw data
    exhibitor = Exhibitor(
        id=exhibitor_row[0],
        code=exhibitor_row[1],
        name=exhibitor_row[2],
        description=exhibitor_row[3],
        latitude=exhibitor_row[4],
        longitude=exhibitor_row[5],
        photo_url=exhibitor_row[6],
        order=exhibitor_row[7],
        is_active=exhibitor_row[8],
        min_persons_per_slot=exhibitor_row[9],
        max_persons_per_slot=exhibitor_row[10],
        open_date=exhibitor_row[11],
        close_date=exhibitor_row[12]
    )

    if data.code is not None:
        # Check if code exists for another exhibitor
        check_result = await db.execute(text(f"SELECT id FROM exhibitors WHERE code = '{data.code}' AND id != '{point_id}'"))
        if check_result.fetchone():
            raise HTTPException(status_code=400, detail="Exhibitor code already exists")
        exhibitor.code = data.code
    
    # Build UPDATE query with only changed fields
    updates = {}
    if data.name is not None:
        updates['name'] = data.name
    if data.description is not None:
        updates['description'] = data.description
    if data.latitude is not None:
        updates['latitude'] = data.latitude
    if data.longitude is not None:
        updates['longitude'] = data.longitude
    if data.photo_url is not None:
        updates['photo_url'] = data.photo_url
    if data.order is not None:
        updates['order'] = data.order
    if data.is_active is not None:
        updates['is_active'] = data.is_active
    if data.min_persons_per_slot is not None:
        updates['min_persons_per_slot'] = data.min_persons_per_slot
    if data.max_persons_per_slot is not None:
        updates['max_persons_per_slot'] = data.max_persons_per_slot
    if data.open_date is not None:
        updates['open_date'] = data.open_date
    if data.close_date is not None:
        updates['close_date'] = data.close_date

    # Execute UPDATE if there are changes
    if updates:
        set_clause = ', '.join([f"{k} = '{v}'" for k, v in updates.items()])
        update_sql = f"UPDATE exhibitors SET {set_clause} WHERE id = '{point_id}'"
        await db.execute(text(update_sql))
        await db.commit()

        # Fetch updated exhibitor
        result = await db.execute(text(f"SELECT id, code, name, description, latitude, longitude, photo_url, \"order\", is_active, min_persons_per_slot, max_persons_per_slot FROM exhibitors WHERE id = '{point_id}'"))
        exhibitor_row = result.fetchone()
        if exhibitor_row:
            exhibitor.code = exhibitor_row[1]
            exhibitor.name = exhibitor_row[2]
            exhibitor.description = exhibitor_row[3]
            exhibitor.latitude = exhibitor_row[4]
            exhibitor.longitude = exhibitor_row[5]
            exhibitor.photo_url = exhibitor_row[6]
            exhibitor.order = exhibitor_row[7]
            exhibitor.is_active = exhibitor_row[8]
            exhibitor.min_persons_per_slot = exhibitor_row[9]
            exhibitor.max_persons_per_slot = exhibitor_row[10]
    
    # Log audit
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "exhibitor_updated", {"exhibitor_id": str(exhibitor.id)})
    
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
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "exhibitor_deleted", {"exhibitor_id": str(point_id)})
    
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
    from sqlalchemy import text

    # Verify exhibitor exists using raw SQL (SQLite async compatibility)
    exhibitor_result = await db.execute(text(f"SELECT id FROM exhibitors WHERE id = '{point_id}'"))
    exhibitor_row = exhibitor_result.fetchone()
    if not exhibitor_row:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    
    from datetime import time as dt_time
    try:
        start_time = dt_time.fromisoformat(data.start_time)
        end_time = dt_time.fromisoformat(data.end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS")
    
    # Validar tipo de franja
    valid_types = ['all_days', 'weekends', 'specific_day']
    if data.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de franja inválido. Debe ser uno de: {', '.join(valid_types)}"
        )

    # Validar minutos: :00 o :30
    if start_time.minute not in [0, 30]:
        raise HTTPException(
            status_code=400,
            detail=f"La hora de inicio debe ser en punto o media hora (:00 o :30). Se recibió {start_time.strftime('%H:%M')}"
        )
    if end_time.minute not in [0, 30]:
        raise HTTPException(
            status_code=400,
            detail=f"La hora de fin debe ser en punto o media hora (:00 o :30). Se recibió {end_time.strftime('%H:%M')}"
        )

    # Validar rango: 6:00 AM a 10:00 PM (22:00)
    min_hour = 6  # 6 AM
    max_hour = 22  # 10 PM
    if start_time.hour < min_hour or (start_time.hour == min_hour and start_time.minute < 0):
        raise HTTPException(
            status_code=400,
            detail=f"La hora de inicio debe ser como mínimo 06:00 (6:00 AM). Se recibió {start_time.strftime('%H:%M')}"
        )
    if end_time.hour > max_hour or (end_time.hour == max_hour and end_time.minute > 0):
        raise HTTPException(
            status_code=400,
            detail=f"La hora de fin debe ser como máximo 22:00 (10:00 PM). Se recibió {end_time.strftime('%H:%M')}"
        )

    # Validar que end_time sea mayor que start_time
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="La hora de fin debe ser posterior a la hora de inicio")

    # Validar weekday según tipo
    if data.type == 'specific_day':
        if data.weekday is None or data.weekday < 0 or data.weekday > 6:
            raise HTTPException(
                status_code=400,
                detail="Para tipo 'specific_day', weekday debe ser un número entre 0 (Lunes) y 6 (Domingo)"
            )
    elif data.type == 'weekends':
        if data.weekday is not None and data.weekday not in [5, 6]:
            raise HTTPException(
                status_code=400,
                detail="Para tipo 'weekends', weekday debe ser 5 (Sábado) o 6 (Domingo)"
            )
    elif data.type == 'all_days':
        if data.weekday is not None:
            raise HTTPException(
                status_code=400,
                detail="Para tipo 'all_days', weekday debe ser NULL (no se especifica día)"
            )
    
    # Crear schedule usando raw SQL INSERT para evitar problemas de greenlet con SQLite async
    import uuid
    schedule_id = str(uuid.uuid4())
    weekday_value = data.weekday if data.weekday is not None else "NULL"

    insert_query = f"""
    INSERT INTO schedules (id, exhibitor_id, type, weekday, start_time, end_time, is_active, created_at)
    VALUES ('{schedule_id}', '{point_id}', '{data.type}', {weekday_value}, '{start_time}', '{end_time}', {1 if data.is_active else 0}, CURRENT_TIMESTAMP)
    """

    await db.execute(text(insert_query))
    await db.commit()

    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "schedule_created", {"schedule_id": schedule_id, "point_id": str(point_id)})

    return {
        "id": schedule_id,
        "type": data.type,
        "weekday": data.weekday,
        "start_time": str(start_time),
        "end_time": str(end_time),
        "is_active": data.is_active
    }

@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    data: ScheduleUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update schedule"""
    # Use raw SQL to fetch schedule (SQLite async UUID issues)
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT id, exhibitor_id, type, weekday, start_time, end_time, is_active, created_at FROM schedules WHERE id = :schedule_id"),
        {"schedule_id": schedule_id}
    )
    schedule_row = result.fetchone()

    if not schedule_row:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Convert raw SQL row to dict for easier manipulation
    schedule = {
        "id": schedule_row[0],
        "exhibitor_id": schedule_row[1],
        "type": schedule_row[2],
        "weekday": schedule_row[3],
        "start_time": schedule_row[4],
        "end_time": schedule_row[5],
        "is_active": schedule_row[6],
        "created_at": schedule_row[7]
    }
    
    # Preparar valores actualizados (usar los nuevos o mantener los existentes)
    from datetime import time as dt_time
    new_type = data.type if data.type is not None else schedule["type"]
    new_weekday = data.weekday if data.weekday is not None else schedule["weekday"]
    new_start_time = dt_time.fromisoformat(data.start_time) if data.start_time else (schedule["start_time"] if isinstance(schedule["start_time"], dt_time) else dt_time.fromisoformat(str(schedule["start_time"])))
    new_end_time = dt_time.fromisoformat(data.end_time) if data.end_time else (schedule["end_time"] if isinstance(schedule["end_time"], dt_time) else dt_time.fromisoformat(str(schedule["end_time"])))

    # Validar tipo de franja
    valid_types = ['all_days', 'weekends', 'specific_day']
    if new_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de franja inválido. Debe ser uno de: {', '.join(valid_types)}"
        )

    # Validar minutos: :00 o :30
    if data.start_time and new_start_time.minute not in [0, 30]:
        raise HTTPException(
            status_code=400,
            detail=f"La hora de inicio debe ser en punto o media hora (:00 o :30). Se recibió {new_start_time.strftime('%H:%M')}"
        )
    if data.end_time and new_end_time.minute not in [0, 30]:
        raise HTTPException(
            status_code=400,
            detail=f"La hora de fin debe ser en punto o media hora (:00 o :30). Se recibió {new_end_time.strftime('%H:%M')}"
        )

    # Validar rango: 6:00 AM a 10:00 PM (22:00)
    min_hour = 6
    max_hour = 22
    if new_start_time.hour < min_hour or (new_start_time.hour == min_hour and new_start_time.minute < 0):
        raise HTTPException(
            status_code=400,
            detail=f"La hora de inicio debe ser como mínimo 06:00 (6:00 AM). Se recibió {new_start_time.strftime('%H:%M')}"
        )
    if new_end_time.hour > max_hour or (new_end_time.hour == max_hour and new_end_time.minute > 0):
        raise HTTPException(
            status_code=400,
            detail=f"La hora de fin debe ser como máximo 22:00 (10:00 PM). Se recibió {new_end_time.strftime('%H:%M')}"
        )

    # Validar que end_time sea mayor que start_time
    if new_end_time <= new_start_time:
        raise HTTPException(status_code=400, detail="La hora de fin debe ser posterior a la hora de inicio")

    # Validar weekday según tipo
    if new_type == 'specific_day':
        if new_weekday is None or new_weekday < 0 or new_weekday > 6:
            raise HTTPException(
                status_code=400,
                detail="Para tipo 'specific_day', weekday debe ser un número entre 0 (Lunes) y 6 (Domingo)"
            )
    elif new_type == 'weekends':
        if new_weekday is not None and new_weekday not in [5, 6]:
            raise HTTPException(
                status_code=400,
                detail="Para tipo 'weekends', weekday debe ser 5 (Sábado) o 6 (Domingo)"
            )
    elif new_type == 'all_days':
        if new_weekday is not None:
            raise HTTPException(
                status_code=400,
                detail="Para tipo 'all_days', weekday debe ser NULL (no se especifica día)"
            )

    # Solo validar solapamiento si se están modificando horas/día y el horario va a estar ACTIVO
    # Si solo se desactiva, no necesita validación de solapamiento
    time_changed = data.start_time is not None or data.end_time is not None or data.weekday is not None
    will_be_active = data.is_active if data.is_active is not None else schedule["is_active"]

    if time_changed and will_be_active:
        # Verificar solapamiento con otros horarios del mismo exhibidor (excluyendo el actual)
        # Use raw SQL for SQLite compatibility
        sql = """
            SELECT id, type, weekday, start_time, end_time, is_active FROM schedules
            WHERE exhibitor_id = :exhibitor_id
            AND id != :schedule_id
            AND is_active = 1
        """
        if new_weekday is not None:
            sql += " AND (weekday = :new_weekday OR weekday IS NULL)"

        params = {
            "exhibitor_id": schedule["exhibitor_id"],
            "schedule_id": schedule_id,
            "new_weekday": new_weekday
        }

        existing_schedules_result = await db.execute(text(sql), params)
        existing_schedules_rows = existing_schedules_result.fetchall()
        existing_schedules = existing_schedules_rows

        # Verificar solapamiento de horarios
        for existing in existing_schedules:
            existing_weekday = existing[2]  # weekday
            existing_start_time_str = existing[3]  # start_time
            existing_end_time_str = existing[4]  # end_time

            # Parse time strings from SQLite
            try:
                existing_start = dt_time.fromisoformat(str(existing_start_time_str).split('.')[0])
                existing_end = dt_time.fromisoformat(str(existing_end_time_str).split('.')[0])
            except (ValueError, AttributeError):
                continue

            weekday_overlaps = (
                existing_weekday is None or
                new_weekday is None or
                existing_weekday == new_weekday
            )

            if weekday_overlaps:
                # Verificar solapamiento de tiempos
                if new_start_time < existing_end and new_end_time > existing_start:
                    # Mapear números de día a nombres
                    weekday_names = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
                    existing_weekday_str = "Todos los días" if existing_weekday is None else weekday_names.get(existing_weekday, f"Día {existing_weekday}")
                    new_weekday_str = "Todos los días" if new_weekday is None else weekday_names.get(new_weekday, f"Día {new_weekday}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"El horario se solapa con uno existente: {existing_start.strftime('%H:%M')}-{existing_end.strftime('%H:%M')} ({existing_weekday_str}). "
                               f"El horario actualizado {new_start_time.strftime('%H:%M')}-{new_end_time.strftime('%H:%M')} ({new_weekday_str}) no puede solaparse con horarios existentes."
                    )
    
    # Preparar cambios
    updates = {}
    if data.type is not None:
        updates["type"] = data.type
        schedule["type"] = data.type

    if data.weekday is not None:
        updates["weekday"] = data.weekday
        schedule["weekday"] = data.weekday

    if data.start_time is not None:
        try:
            updates["start_time"] = data.start_time
            schedule["start_time"] = data.start_time
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS")

    if data.end_time is not None:
        try:
            updates["end_time"] = data.end_time
            schedule["end_time"] = data.end_time
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM:SS")

    if data.is_active is not None:
        updates["is_active"] = 1 if data.is_active else 0
        schedule["is_active"] = data.is_active

    # Aplicar cambios con raw SQL UPDATE
    if updates:
        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        update_sql = f"UPDATE schedules SET {set_clause} WHERE id = :schedule_id"
        await db.execute(text(update_sql), {**updates, "schedule_id": schedule_id})
        await db.commit()

    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "schedule_updated", {"schedule_id": str(schedule_id), "is_active": schedule["is_active"]})

    return {
        "id": str(schedule["id"]),
        "type": schedule["type"],
        "weekday": schedule["weekday"],
        "start_time": str(schedule["start_time"]),
        "end_time": str(schedule["end_time"]),
        "is_active": schedule["is_active"]
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
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "schedule_deleted", {"schedule_id": str(schedule_id)})
    
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
    
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "user_created", {"user_id": str(user.id)})
    
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
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "user_updated", {"user_id": str(user.id)})
    
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
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "user_deleted", {"user_id": str(user_id)})
    
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

@router.get("/hermanos/available")
async def get_available_hermanos(
    exhibitor_id: UUID = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all active male hermanos available for assignment"""
    from sqlalchemy import text

    # Get all active hermanos ordered by name
    result = await db.execute(
        text("SELECT id, nombre, congregacion, telefono, genero FROM hermanos WHERE is_active = 1 ORDER BY nombre")
    )
    all_hermanos_rows = result.fetchall()

    # Get existing hermano_ids already assigned to THIS exhibitor
    existing_hermano_ids = set()
    if exhibitor_id:
        existing_result = await db.execute(
            text("""
                SELECT DISTINCT a.hermano_id
                FROM admins a
                JOIN exhibitor_leaders el ON a.id = el.admin_id
                WHERE el.exhibitor_id = :exhibitor_id AND a.hermano_id IS NOT NULL
            """),
            {"exhibitor_id": str(exhibitor_id)}
        )
        existing_hermano_ids = {str(hid[0]) for hid in existing_result.fetchall()}

    # Filter: only varones (male hermanos), showing all regardless of other exhibitor assignments
    available = []
    for row in all_hermanos_rows:
        hermano_id, nombre, congregacion, telefono, genero = row

        # Detect gender if not stored
        actual_gender = genero or detect_gender_from_name(nombre)

        # Only include varones (not hermanas)
        if actual_gender != "hermana":
            is_assigned_here = str(hermano_id) in existing_hermano_ids

            available.append({
                "id": str(hermano_id),
                "nombre": nombre,
                "congregacion": congregacion,
                "telefono": telefono,
                "genero": actual_gender,
                "gender_label": get_gender_label(nombre) if not genero else ("Hermana" if genero == "hermana" else "Hermano"),
                "is_assigned_here": is_assigned_here
            })

    return available

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
    # - encargado: encargado de uno o más puntos de exhibidor (principal o auxiliar)
    role: str = "encargado"

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

    if data.user_id:
        return {
            "id": str(new_admin.id),
            "user_id": str(new_admin.user_id),
            "hermano_id": None,
            "username": new_admin.username,
            "role": new_admin.role,
            "user": {
                "id": str(user.id),
                "full_name": user.full_name,
                "phone": user.phone
            },
            "hermano": None
        }
    else:
        return {
            "id": str(new_admin.id),
            "user_id": None,
            "hermano_id": str(new_admin.hermano_id),
            "username": new_admin.username,
            "role": new_admin.role,
            "user": None,
            "hermano": {
                "id": str(hermano.id),
                "nombre": hermano.nombre,
                "congregacion": hermano.congregacion,
                "telefono": hermano.telefono
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
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "admin_updated", {"admin_id": str(admin_id)})

    if admin_obj.user_id:
        user_result = await db.execute(select(User).where(User.id == admin_obj.user_id))
        user = user_result.scalar_one_or_none()
        return {
            "id": str(admin_obj.id),
            "user_id": str(admin_obj.user_id),
            "hermano_id": None,
            "username": admin_obj.username,
            "role": admin_obj.role,
            "user": {"id": str(user.id), "full_name": user.full_name, "phone": user.phone} if user else None,
            "hermano": None
        }
    else:
        hermano_result = await db.execute(select(Hermano).where(Hermano.id == admin_obj.hermano_id))
        hermano = hermano_result.scalar_one_or_none()
        return {
            "id": str(admin_obj.id),
            "user_id": None,
            "hermano_id": str(admin_obj.hermano_id),
            "username": admin_obj.username,
            "role": admin_obj.role,
            "user": None,
            "hermano": {"id": str(hermano.id), "nombre": hermano.nombre, "congregacion": hermano.congregacion, "telefono": hermano.telefono} if hermano else None
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
    await log_audit(db, admin.user_id or admin.hermano_id, "admin", "admin_deleted", {"admin_id": str(admin_id)})
    
    return {"message": "Admin deleted"}


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
    exhibitor_id: UUID = Query(None),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all exhibitor leaders. Si se proporciona exhibitor_id, solo retorna líderes de ese exhibidor."""
    query = select(ExhibitorLeader, Admin, Exhibitor)
    if exhibitor_id:
        query = query.where(ExhibitorLeader.exhibitor_id == exhibitor_id)
    
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
    
    if admin_obj.role not in ("encargado", "lider_exhibidor"):
        raise HTTPException(status_code=400, detail="El admin debe tener rol 'encargado'")
    
    # Verificar que el exhibitor existe
    exhibitor_result = await db.execute(select(Exhibitor).where(Exhibitor.id == UUID(data.exhibitor_id)))
    exhibitor = exhibitor_result.scalar_one_or_none()
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor no encontrado")
    
    # Validar posición
    valid_positions = ["principal", "auxiliar", "publicaciones", "mantenimiento", "encargado",
                       "suplente", "encargado_turnos_principal", "encargado_turnos_remplazo", "publicaciones_mantenimiento"]
    if data.position not in valid_positions:
        raise HTTPException(status_code=400, detail=f"Position debe ser uno de: {', '.join(valid_positions)}")

    # Verificar que no haya ya un líder con la misma posición para este exhibidor
    # Solo las posiciones únicas deben validarse
    unique_positions = ["principal", "encargado", "encargado_turnos_principal"]
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
        
        if admin_obj.role not in ("encargado", "lider_exhibidor"):
            raise HTTPException(status_code=400, detail="El admin debe tener rol 'encargado'")

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
        valid_positions = ["principal", "auxiliar", "publicaciones", "mantenimiento", "encargado",
                           "suplente", "encargado_turnos_principal", "encargado_turnos_remplazo", "publicaciones_mantenimiento"]
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
        raise HTTPException(status_code=403, detail="Solo super administradores pueden gestionar encargados de punto")

    result = await db.execute(select(ExhibitorLeader).where(ExhibitorLeader.id == UUID(leader_id)))
    leader = result.scalar_one_or_none()

    if not leader:
        raise HTTPException(status_code=404, detail="Encargado no encontrado")

    await db.execute(delete(ExhibitorLeader).where(ExhibitorLeader.id == UUID(leader_id)))
    await db.commit()

    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "exhibitor_leader_deleted", {"leader_id": str(leader_id)})

    return {"message": "Encargado de punto eliminado"}


@router.post("/exhibitor-leaders/from-hermano")
async def assign_hermano_as_leader(
    data: dict,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Assign a hermano as exhibitor leader. Creates admin record if needed."""
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Solo super administradores pueden gestionar líderes")

    hermano_id = data.get('hermano_id')
    exhibitor_id = data.get('exhibitor_id')
    position = data.get('position', 'principal')

    if not hermano_id or not exhibitor_id:
        raise HTTPException(status_code=400, detail="Debe proporcionar hermano_id y exhibitor_id")

    # Verify hermano exists
    hermano_result = await db.execute(select(Hermano).where(Hermano.id == UUID(hermano_id)))
    hermano = hermano_result.scalar_one_or_none()
    if not hermano:
        raise HTTPException(status_code=404, detail="Hermano no encontrado")

    # Verify exhibitor exists
    exhibitor_result = await db.execute(select(Exhibitor).where(Exhibitor.id == UUID(exhibitor_id)))
    exhibitor = exhibitor_result.scalar_one_or_none()
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibidor no encontrado")

    # Check if admin exists for this hermano
    admin_result = await db.execute(select(Admin).where(Admin.hermano_id == UUID(hermano_id)))
    admin_obj = admin_result.scalar_one_or_none()

    if not admin_obj:
        # Create admin for hermano with generated username and password
        import secrets
        import string
        username = f"encargado_{hermano.nombre[:10].lower().replace(' ', '_')}_{secrets.token_hex(3)}"
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

        admin_obj = Admin(
            hermano_id=UUID(hermano_id),
            username=username,
            password_hash=pwd_context.hash(password),
            role="encargado"
        )
        db.add(admin_obj)
        await db.flush()  # Get the ID without committing

    # Create ExhibitorLeader
    valid_positions = ["principal", "auxiliar", "publicaciones", "mantenimiento", "encargado",
                       "suplente", "encargado_turnos_principal", "encargado_turnos_remplazo", "publicaciones_mantenimiento"]
    if position not in valid_positions:
        raise HTTPException(status_code=400, detail=f"Position debe ser uno de: {', '.join(valid_positions)}")

    # Check for unique positions
    unique_positions = ["principal", "encargado", "encargado_turnos_principal"]
    if position in unique_positions:
        existing = await db.execute(
            select(ExhibitorLeader).where(
                ExhibitorLeader.exhibitor_id == UUID(exhibitor_id),
                ExhibitorLeader.position == position
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Ya existe un líder con posición {position} en este exhibidor")

    # Check if hermano already has this position in this exhibitor
    existing_leader = await db.execute(
        select(ExhibitorLeader).where(
            ExhibitorLeader.admin_id == admin_obj.id,
            ExhibitorLeader.exhibitor_id == UUID(exhibitor_id),
            ExhibitorLeader.position == position
        )
    )
    if existing_leader.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Este hermano ya tiene esta posición en este exhibidor")

    leader = ExhibitorLeader(
        admin_id=admin_obj.id,
        exhibitor_id=UUID(exhibitor_id),
        position=position
    )
    db.add(leader)
    await db.commit()
    await db.refresh(leader)

    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "hermano_assigned_as_leader", {
        "hermano_id": hermano_id,
        "exhibitor_id": exhibitor_id,
        "position": position
    })

    return {
        "id": str(leader.id),
        "admin_id": str(leader.admin_id),
        "hermano_id": hermano_id,
        "hermano_name": hermano.nombre,
        "exhibitor_id": str(leader.exhibitor_id),
        "position": leader.position
    }


# ── AppSettings: configuración global del sistema ───────────────────────────
from app.models import AppSetting

class AppSettingUpdate(BaseModel):
    value: dict | list | str | int | float | bool

@router.get("/settings")
async def get_settings(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Obtener todas las configuraciones del sistema."""
    result = await db.execute(select(AppSetting))
    settings_list = result.scalars().all()
    return {s.key: s.value for s in settings_list}

@router.put("/settings/{key}")
async def update_setting(
    key: str,
    data: AppSettingUpdate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Actualizar una configuración del sistema. Solo super_admin."""
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Solo super administradores pueden modificar configuraciones")

    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = data.value
    else:
        setting = AppSetting(key=key, value=data.value)
        db.add(setting)

    await db.commit()
    actor_id = admin.user_id or admin.hermano_id
    await log_audit(db, actor_id, "admin", "setting_updated", {"key": key, "value": data.value})

    return {"key": key, "value": data.value}


# ── Estadísticas mensuales de turnos por hermano ─────────────────────────────

@router.get("/stats/monthly-turns")
async def get_monthly_turns_stats(
    exhibitor_id: str = None,
    year: int = None,
    month: int = None,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Estadísticas de turnos por hermano en el mes.
    Incluye indicador visual para quienes superan el límite configurable.
    Encargados solo ven sus exhibidores asignados.
    """
    from datetime import date as date_type
    import calendar as cal_module

    today = date_type.today()
    target_year = year or today.year
    target_month = month or today.month

    first_of_month = date_type(target_year, target_month, 1)
    last_of_month = date_type(target_year, target_month, cal_module.monthrange(target_year, target_month)[1])

    # Obtener límite configurable desde AppSetting (default 10)
    setting_result = await db.execute(
        select(AppSetting).where(AppSetting.key == "monthly_turn_limit")
    )
    setting = setting_result.scalar_one_or_none()
    monthly_limit = int(setting.value) if setting and setting.value else 10

    # Filtrar por exhibidores si es encargado
    exhibitor_filter = []
    if admin.role in ("encargado", "lider_exhibidor"):
        leaders_result = await db.execute(
            select(ExhibitorLeader.exhibitor_id).where(ExhibitorLeader.admin_id == admin.id)
        )
        exhibitor_filter = [row[0] for row in leaders_result.all()]
        if not exhibitor_filter:
            return {"stats": [], "monthly_limit": monthly_limit, "period": f"{target_year}-{target_month:02d}"}

    # Query base: contar turnos aprobados por usuario + exhibidor en el mes
    query = (
        select(
            User.id.label("user_id"),
            User.full_name.label("user_name"),
            User.phone.label("user_phone"),
            Exhibitor.id.label("exhibitor_id"),
            Exhibitor.name.label("exhibitor_name"),
            func.count(RequestItem.id).label("turn_count")
        )
        .join(Request, Request.user_id == User.id)
        .join(RequestItem, RequestItem.request_id == Request.id)
        .join(Slot, RequestItem.slot_id == Slot.id)
        .join(Exhibitor, Slot.exhibitor_id == Exhibitor.id)
        .where(
            RequestItem.status == "approved",
            Slot.slot_date >= first_of_month,
            Slot.slot_date <= last_of_month
        )
        .group_by(User.id, User.full_name, User.phone, Exhibitor.id, Exhibitor.name)
        .order_by(func.count(RequestItem.id).desc())
    )

    if exhibitor_id:
        query = query.where(Exhibitor.id == UUID(exhibitor_id))
    elif exhibitor_filter:
        query = query.where(Exhibitor.id.in_(exhibitor_filter))

    result = await db.execute(query)
    rows = result.all()

    stats = []
    for row in rows:
        # Try to get congregation from hermanos table
        congregacion = None
        if row.user_phone:
            phone_clean = re.sub(r'\D', '', row.user_phone)
            hermano_result = await db.execute(
                select(Hermano).where(
                    Hermano.is_active == True,
                    Hermano.telefono.like(f'%{phone_clean}%')
                ).limit(1)
            )
            hermano = hermano_result.scalar_one_or_none()
            if hermano:
                congregacion = hermano.congregacion

        stats.append({
            "user_id": str(row.user_id),
            "user_name": row.user_name,
            "user_phone": row.user_phone,
            "congregacion": congregacion,
            "exhibitor_id": str(row.exhibitor_id),
            "exhibitor_name": row.exhibitor_name,
            "turn_count": row.turn_count,
            "exceeds_limit": row.turn_count >= monthly_limit,
            "near_limit": row.turn_count >= (monthly_limit * 0.8) and row.turn_count < monthly_limit
        })

    return {
        "stats": stats,
        "monthly_limit": monthly_limit,
        "period": f"{target_year}-{target_month:02d}",
        "total_users": len(set(r["user_id"] for r in stats)),
        "users_exceeding_limit": sum(1 for r in stats if r["exceeds_limit"])
    }


# ── Endpoint: consulta de turnos de hermano (módulo usuario desde admin) ─────

@router.get("/hermano-turns")
async def get_hermano_turns_admin(
    phone: str,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Consulta los turnos de un hermano por teléfono.
    Disponible desde el panel de administrador.
    """
    import re
    phone_clean = re.sub(r'\D', '', phone)
    if not phone_clean or len(phone_clean) < 7:
        raise HTTPException(status_code=400, detail="Teléfono inválido")

    hermano_result = await db.execute(
        select(Hermano).where(
            Hermano.is_active == True,
            Hermano.telefono.like(f'%{phone_clean}%')
        ).limit(1)
    )
    hermano = hermano_result.scalar_one_or_none()

    user_result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.phone.like(f'%{phone_clean}%')
        ).limit(1)
    )
    user = user_result.scalar_one_or_none()

    if not hermano and not user:
        raise HTTPException(status_code=404, detail="Hermano no encontrado")

    display_name = hermano.nombre if hermano else (user.full_name if user else "Desconocido")
    congregacion = hermano.congregacion if hermano else None
    user_id = user.id if user else None

    if not user_id:
        return {"found": True, "name": display_name, "congregacion": congregacion, "turns": [], "total": 0}

    items_result = await db.execute(
        select(RequestItem, Slot, Schedule, Exhibitor)
        .join(Request, RequestItem.request_id == Request.id)
        .join(Slot, RequestItem.slot_id == Slot.id)
        .join(Schedule, Slot.schedule_id == Schedule.id)
        .join(Exhibitor, Slot.exhibitor_id == Exhibitor.id)
        .where(
            Request.user_id == user_id,
            RequestItem.status == "approved"
        )
        .order_by(Slot.slot_date, Schedule.start_time)
    )
    items_data = items_result.all()

    turns = []
    for req_item, slot, schedule, exhibitor in items_data:
        turns.append({
            "item_id": str(req_item.id),
            "exhibitor_name": exhibitor.name,
            "exhibitor_code": exhibitor.code,
            "date": slot.slot_date.isoformat(),
            "start_time": str(schedule.start_time),
            "end_time": str(schedule.end_time),
            "status": req_item.status
        })

    return {
        "found": True,
        "name": display_name,
        "congregacion": congregacion,
        "turns": turns,
        "total": len(turns)
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics - unique source of truth for occupancy rates"""
    from datetime import datetime, date
    from dateutil.relativedelta import relativedelta

    today = date.today()
    month_start = today.replace(day=1)
    month_end = (today + relativedelta(months=1)).replace(day=1) - relativedelta(days=1)

    # Get all slots for this month
    slots_result = await db.execute(
        select(Slot)
        .where(Slot.slot_date >= month_start)
        .where(Slot.slot_date <= month_end)
    )
    all_slots = slots_result.scalars().all()
    total_slots = len(all_slots)

    # Get all approved RequestItems for this month's slots (optimized single query)
    approved_items_result = await db.execute(
        select(RequestItem.slot_id)
        .distinct()
        .where(RequestItem.status == "approved")
    )
    occupied_slot_ids = set(item[0] for item in approved_items_result.all() if item[0])

    # Count occupied slots (slots with at least one approved RequestItem)
    occupied_slots = sum(1 for slot in all_slots if slot.id in occupied_slot_ids)

    # Calculate occupancy rate safely (never NaN or Infinity)
    if total_slots > 0:
        occupancy_rate = round((occupied_slots / total_slots) * 100, 1)
    else:
        occupancy_rate = 0

    # Get all requests for this month
    requests_result = await db.execute(
        select(Request)
        .where(cast(Request.created_at, Date) >= month_start)
        .where(cast(Request.created_at, Date) <= month_end)
    )
    all_requests = requests_result.scalars().all()
    total_requests = len(all_requests)
    approved_requests = sum(1 for r in all_requests if r.status == "approved")

    # Get unique users with approved requests
    approved_items_result = await db.execute(
        select(Request.user_id)
        .distinct()
        .where(cast(Request.created_at, Date) >= month_start)
        .where(cast(Request.created_at, Date) <= month_end)
        .where(Request.status == "approved")
    )
    approved_items = approved_items_result.all()
    participating_hermanos = len([item[0] for item in approved_items if item[0]])

    # Get active exhibitors for current month
    exhibitors_result = await db.execute(
        select(Exhibitor)
        .where(Exhibitor.is_active == True)
        .where(Exhibitor.is_open_for_requests == True)
        .where(Exhibitor.open_date <= month_end)
        .where(Exhibitor.close_date >= month_start)
    )
    active_exhibitors = len(exhibitors_result.scalars().all())

    # Ensure all values are valid numbers (never NaN, Infinity, null, etc.)
    return {
        "occupancy_rate": float(occupancy_rate) if isinstance(occupancy_rate, (int, float)) else 0,
        "total_requests": int(total_requests),
        "approved_requests": int(approved_requests),
        "participating_hermanos": int(participating_hermanos),
        "active_exhibitors": int(active_exhibitors),
        "total_slots": int(total_slots),
        "occupied_slots": int(occupied_slots),
        "available_slots": int(max(total_slots - occupied_slots, 0))
    }
