from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models import Exhibitor, Schedule, Slot, RequestItem, Request, ExhibitorLeader, Admin, User, Hermano
from app.config import settings
from sqlalchemy import func
from uuid import UUID

router = APIRouter()

class ScheduleResponse(BaseModel):
    id: str
    weekday: int | None = None
    start_time: str
    end_time: str
    is_active: bool
    availability: dict | None = None  # {date: {current: int, capacity: int, available: bool}}

class ExhibitorLeaderResponse(BaseModel):
    id: str
    admin_id: str
    admin_name: str | None = None
    position: str

class ExhibitorResponse(BaseModel):
    id: str
    code: str | None = None
    name: str
    description: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    photo_url: str | None = None
    is_active: bool
    min_persons_per_slot: int = 3
    max_persons_per_slot: int = 5
    open_date: str | None = None
    close_date: str | None = None
    is_open_for_requests: bool = True  # Indica si está abierto para solicitudes
    schedules: List[ScheduleResponse]
    leaders: List[ExhibitorLeaderResponse] = []

@router.get("", response_model=List[ExhibitorResponse])
async def get_exhibitors(
    from_date: date = Query(None),
    to_date: date = Query(None),
    active_only: bool = True,
    phone: str = Query(None),
    include_all_schedules: bool = Query(False, description="Incluir todos los schedules incluso si no hay disponibilidad (útil para admin)"),
    db: AsyncSession = Depends(get_db)
):
    """Get all exhibitors (puntos de exhibidor) with their schedules"""
    query = select(Exhibitor)
    if active_only:
        query = query.where(Exhibitor.is_active == True)
    
    result = await db.execute(query.order_by(Exhibitor.code, Exhibitor.order))
    exhibitors = result.scalars().all()
    
    today = date.today()
    
    # Obtener el usuario por teléfono si se proporciona
    user_id = None
    if phone:
        import re
        phone_clean = re.sub(r'\D', '', phone)
        if phone_clean and len(phone_clean) >= 7:
            user_result = await db.execute(
                select(User).where(User.phone.like(f'%{phone_clean}%'), User.is_active == True)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_id = user.id
    
    response = []
    for exhibitor in exhibitors:
        # Verificar si el exhibidor está abierto para solicitudes
        # IMPORTANTE: Apertura a las 00:00:00 del día open_date y cierre hasta las 23:59:59 del close_date
        is_open_for_requests = True
        if exhibitor.open_date and exhibitor.close_date:
            # La plataforma está abierta entre open_date (00:00:00) y close_date (23:59:59)
            # open_date <= today <= close_date (inclusivo en ambos extremos)
            is_open_for_requests = exhibitor.open_date <= today <= exhibitor.close_date
        elif exhibitor.open_date:
            # Solo tiene open_date, está abierto desde esa fecha a las 00:00:00
            is_open_for_requests = today >= exhibitor.open_date
        elif exhibitor.close_date:
            # Solo tiene close_date, está abierto hasta esa fecha a las 23:59:59
            is_open_for_requests = today <= exhibitor.close_date
        
        # Calcular rango de fechas para mostrar disponibilidad
        # LÓGICA NUEVA: Mostrar SOLO el mes siguiente (no el mes actual)
        # Ejemplo: Si open_date=2025-12-20 y close_date=2026-01-31
        #          Muestra SOLO días de ENERO 2026 (1 al 31)
        if exhibitor.open_date and exhibitor.close_date:
            # Verificar que estamos en el período de apertura
            if today < exhibitor.open_date:
                # Aún no ha abierto
                date_range = []
            elif today > exhibitor.close_date:
                # Ya cerró
                date_range = []
            else:
                # Estamos en el período de apertura
                # Mostrar el mes del close_date (el mes objetivo)
                target_year = exhibitor.close_date.year
                target_month = exhibitor.close_date.month
                
                # Primer día del mes objetivo
                first_day = date(target_year, target_month, 1)
                # Último día es el close_date
                last_day = exhibitor.close_date
                
                # Generar todos los días del mes objetivo
                date_range = []
                current_date = first_day
                while current_date <= last_day:
                    date_range.append(current_date)
                    current_date += timedelta(days=1)
        else:
            # Si no tiene ambas fechas configuradas, no mostrar
            date_range = []
        # Get schedules - filter by is_active only if active_only is True
        # Ordenar por hora de inicio (start_time)
        schedule_query = select(Schedule).where(Schedule.exhibitor_id == exhibitor.id)
        if active_only:
            schedule_query = schedule_query.where(Schedule.is_active == True)
        schedule_query = schedule_query.order_by(Schedule.start_time)
        schedules_result = await db.execute(schedule_query)
        schedules = schedules_result.scalars().all()
        
        # Build availability info for each schedule
        schedules_with_availability = []
        for s in schedules:
            availability = {}
            now = datetime.now()
            
            # For each date in range, check slot availability
            for check_date in date_range:
                # Filter by weekday: if schedule has a specific weekday, only show that day
                # weekday: 0=Lunes, 1=Martes, ..., 6=Domingo (Python datetime.weekday())
                if s.weekday is not None:
                    # Python's weekday(): Monday=0, Sunday=6
                    if check_date.weekday() != s.weekday:
                        # Skip this date if it doesn't match the schedule's weekday
                        continue
                
                # Find or estimate slot for this date
                slot_result = await db.execute(
                    select(Slot).where(
                        Slot.exhibitor_id == exhibitor.id,
                        Slot.schedule_id == s.id,
                        Slot.slot_date == check_date
                    )
                )
                slot = slot_result.scalar_one_or_none()
                
                # Calculate start time for this slot
                start_datetime = datetime.combine(check_date, s.start_time)
                
                # Check time constraints:
                # 1. Turno no puede estar en el pasado
                # 2. Si es el mismo día, debe tener al menos 30 minutos de anticipación
                is_past = start_datetime < now
                is_too_soon = False
                if check_date == now.date():
                    time_until_start = (start_datetime - now).total_seconds() / 60  # minutes
                    is_too_soon = time_until_start < 30
                
                if slot:
                    # VERIFICAR SI EL USUARIO YA TIENE ESTE SLOT APROBADO
                    user_has_slot = False
                    if user_id:
                        user_slot_result = await db.execute(
                            select(RequestItem).join(Request).where(
                                RequestItem.slot_id == slot.id,
                                Request.user_id == user_id,
                                RequestItem.status == "approved"
                            )
                        )
                        user_has_slot = user_slot_result.scalar_one_or_none() is not None
                    
                    # Count ONLY approved requests (todas son auto-aprobadas)
                    approved_result = await db.execute(
                        select(func.count(RequestItem.id)).where(
                            RequestItem.slot_id == slot.id,
                            RequestItem.status == "approved"  # Solo aprobadas (auto-aprobación)
                        )
                    )
                    approved_count = approved_result.scalar() or 0
                    
                    # Use exhibitor's max_persons_per_slot capacity
                    capacity = exhibitor.max_persons_per_slot or 5
                    current_count = approved_count  # Solo contamos aprobadas
                    
                    # IMPORTANTE: available_count debe reflejar los cupos disponibles para OTROS usuarios
                    # Si el usuario ya tiene el slot, available_count sigue siendo correcto porque
                    # current_count ya incluye al usuario, así que available_count = capacity - current_count
                    # es correcto (representa cupos disponibles para otros)
                    available_count = capacity - current_count
                    
                    # Check if slot meets minimum requirement
                    min_persons = exhibitor.min_persons_per_slot or 3
                    is_confirmed = current_count >= min_persons
                    
                    # Available only if not past, not too soon, has capacity, and exhibitor is open
                    # IMPORTANTE: Si el usuario ya tiene el slot, NO está disponible para él
                    # pero el slot SÍ se incluye en el cálculo para mantener totalCapacity consistente
                    available = not is_past and not is_too_soon and current_count < capacity and is_open_for_requests and not user_has_slot
                    
                    # INCLUIR TODOS LOS SLOTS (incluso llenos y los que el usuario ya tiene)
                    # para cálculo correcto de porcentaje en frontend
                    # Los slots llenos se marcan como available: false y available_count: 0
                    # Los slots que el usuario ya tiene se marcan como available: false pero
                    # se incluyen en el cálculo para que totalCapacity sea consistente
                else:
                    # No slot exists yet, so it's available (will be created on first request)
                    approved_count = 0
                    capacity = exhibitor.max_persons_per_slot or 5
                    current_count = 0
                    available_count = capacity
                    is_confirmed = False
                    # Available only if not past, not too soon, and exhibitor is open
                    available = not is_past and not is_too_soon and is_open_for_requests
                
                # INCLUIR TODOS LOS SLOTS (incluso llenos y los que el usuario ya tiene) 
                # para cálculo correcto de porcentaje
                # Esto permite que el frontend calcule correctamente la disponibilidad total del día
                # IMPORTANTE: Incluir el slot aunque el usuario ya lo tenga, para que totalCapacity
                # sea consistente entre todos los usuarios
                availability[check_date.isoformat()] = {
                    "current": current_count,
                    "capacity": capacity,
                    "available": available,  # False si el usuario ya tiene el slot o está lleno
                    "available_count": available_count,  # 0 si está lleno (pero cuenta en totalCapacity)
                    "approved_count": approved_count,
                    "is_confirmed": is_confirmed,  # True si tiene mínimo de personas
                    "is_past": is_past,
                    "is_too_soon": is_too_soon,
                    "is_full": current_count >= capacity,  # Indica si está completamente lleno
                    "user_has_slot": user_has_slot  # Indica si el usuario actual ya tiene este slot
                }
            
            # Incluir TODOS los schedules (incluso si todos sus slots están llenos)
            # Esto permite que el frontend calcule correctamente el porcentaje de disponibilidad
            # IMPORTANTE: Si include_all_schedules es True (admin), incluir todos los schedules
            # incluso si no tienen disponibilidad (availability vacío)
            if len(availability) > 0 or include_all_schedules:
                schedules_with_availability.append({
                    "id": str(s.id),
                    "weekday": s.weekday,
                    "start_time": str(s.start_time),
                    "end_time": str(s.end_time),
                    "is_active": s.is_active,
                    "availability": availability  # Puede estar vacío si include_all_schedules=True y el exhibidor está cerrado
                })
        
        # Verificar si el exhibidor está completamente lleno (100%)
        is_exhibitor_full = len(schedules_with_availability) == 0 and len(date_range) > 0
        
        # Calcular próxima fecha de apertura (para el siguiente mes)
        next_open_date = None
        if exhibitor.open_date and exhibitor.close_date:
            # Calcular el siguiente ciclo (mismo día del siguiente mes)
            from dateutil.relativedelta import relativedelta
            try:
                next_open_date = exhibitor.open_date + relativedelta(months=1)
            except:
                # Si falla, calcular manualmente
                next_month = exhibitor.open_date.month + 1
                next_year = exhibitor.open_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                next_open_date = date(next_year, next_month, exhibitor.open_date.day)
        
        # Obtener líderes del exhibidor con joins optimizados
        leaders_result = await db.execute(
            select(ExhibitorLeader, Admin, User, Hermano)
            .join(Admin, ExhibitorLeader.admin_id == Admin.id)
            .outerjoin(User, Admin.user_id == User.id)
            .outerjoin(Hermano, Admin.hermano_id == Hermano.id)
            .where(ExhibitorLeader.exhibitor_id == exhibitor.id)
            .order_by(ExhibitorLeader.position)
        )
        leaders_data = leaders_result.all()
        
        leaders = []
        for leader, admin_obj, user_obj, hermano_obj in leaders_data:
            # Obtener nombre del admin (ya está en el join)
            admin_name = None
            if user_obj:
                admin_name = user_obj.full_name
            elif hermano_obj:
                admin_name = hermano_obj.nombre
            
            leaders.append({
                "id": str(leader.id),
                "admin_id": str(leader.admin_id),
                "admin_name": admin_name,
                "position": leader.position
            })
        
        response.append({
            "id": str(exhibitor.id),
            "code": exhibitor.code,
            "name": exhibitor.name,
            "description": exhibitor.description,
            "latitude": float(exhibitor.latitude) if exhibitor.latitude else None,
            "longitude": float(exhibitor.longitude) if exhibitor.longitude else None,
            "photo_url": exhibitor.photo_url,
            "is_active": exhibitor.is_active,
            "min_persons_per_slot": exhibitor.min_persons_per_slot or 3,
            "max_persons_per_slot": exhibitor.max_persons_per_slot or 5,
            "open_date": exhibitor.open_date.isoformat() if exhibitor.open_date else None,
            "close_date": exhibitor.close_date.isoformat() if exhibitor.close_date else None,
            "is_open_for_requests": is_open_for_requests,
            "is_exhibitor_full": is_exhibitor_full,  # Nuevo: indica si está 100% lleno
            "next_open_date": next_open_date.isoformat() if next_open_date else None,  # Nuevo: próxima apertura
            "schedules": schedules_with_availability,
            "leaders": leaders
        })
    
    return response
