"""Enhanced Point Admin endpoints with analytics and audit trail."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta
from typing import List, Optional

from app.database import get_db
from app.models import Admin, AuditLog, RequestItem, Slot
from app.utils.security import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/point-admin", tags=["Point Admin Enhanced"])

# ==================== AUDITORÍA ====================
@router.get("/audit-trail")
async def get_audit_trail(
    days: int = Query(7, ge=1, le=90),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get audit trail of actions by admins in this point."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")
    admin_id = current_user.get("sub")

    # Get audit logs for this admin from last N days
    since = datetime.utcnow() - timedelta(days=days)

    query = select(AuditLog).where(
        AuditLog.admin_id == admin_id,
        AuditLog.created_at >= since
    ).order_by(desc(AuditLog.created_at))

    # Count total
    count_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.admin_id == admin_id,
            AuditLog.created_at >= since
        )
    )
    total = count_result.scalar()

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    data = [
        {
            "id": str(log.id),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "details": log.details or {},
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]

    return {
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }

# ==================== GRÁFICOS - OCUPACIÓN POR DÍA ====================
@router.get("/analytics/occupancy-daily")
async def get_daily_occupancy(
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily occupancy rate for the last N days."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")
    since = datetime.utcnow() - timedelta(days=days)

    # Get slots created/updated in this period
    result = await db.execute(
        select(
            func.date(Slot.created_at).label("date"),
            func.count(Slot.id).filter(Slot.status == "taken").label("taken"),
            func.count(Slot.id).label("total")
        ).where(
            Slot.exhibitor_id == exhibitor_id,
            Slot.created_at >= since
        ).group_by(func.date(Slot.created_at))
        .order_by(func.date(Slot.created_at))
    )

    records = result.all()

    data = [
        {
            "date": str(record[0]),
            "taken": record[1] or 0,
            "total": record[2] or 0,
            "occupancy_percent": int((record[1] / record[2] * 100) if record[2] > 0 else 0)
        }
        for record in records
    ]

    return {
        "data": data,
        "period_days": days,
        "average_occupancy": int(sum(d["occupancy_percent"] for d in data) / len(data)) if data else 0
    }

# ==================== GRÁFICOS - SOLICITUDES POR SEMANA ====================
@router.get("/analytics/requests-weekly")
async def get_weekly_requests(
    weeks: int = Query(4, ge=1, le=12),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get weekly request statistics."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")
    since = datetime.utcnow() - timedelta(weeks=weeks)

    # Get request counts by week
    result = await db.execute(
        select(
            func.strftime('%Y-%W', RequestItem.created_at).label("week"),
            func.count(RequestItem.id).filter(RequestItem.status == "available").label("available"),
            func.count(RequestItem.id).filter(RequestItem.status == "taken").label("taken"),
            func.count(RequestItem.id).label("total")
        ).where(
            RequestItem.exhibitor_id == exhibitor_id,
            RequestItem.created_at >= since
        ).group_by(func.strftime('%Y-%W', RequestItem.created_at))
    )

    records = result.all()

    data = [
        {
            "week": record[0],
            "available": record[1] or 0,
            "taken": record[2] or 0,
            "total": record[3] or 0
        }
        for record in records
    ]

    return {
        "data": data,
        "period_weeks": weeks
    }

# ==================== FILTROS - SOLICITUDES AVANZADO ====================
@router.get("/requests-filtered")
async def get_filtered_requests(
    status: Optional[str] = Query(None),
    congregation: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get filtered requests with advanced filters."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")

    # Build query
    from app.models import Request, Hermano

    query = select(Request).where(Request.exhibitor_id == exhibitor_id)

    if status:
        query = query.where(Request.status == status)

    if congregation:
        query = query.join(Hermano).where(Hermano.congregacion == congregation)

    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.where(Request.created_at >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.where(Request.created_at <= to_date)
        except ValueError:
            pass

    # Count
    count_result = await db.execute(
        select(func.count(Request.id)).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Paginate
    query = query.order_by(desc(Request.created_at))
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    requests = result.scalars().all()

    data = [
        {
            "id": str(req.id),
            "hermano_id": str(req.hermano_id),
            "status": req.status,
            "created_at": req.created_at.isoformat()
        }
        for req in requests
    ]

    return {
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        },
        "filters_applied": {
            "status": status,
            "congregation": congregation,
            "date_from": date_from,
            "date_to": date_to
        }
    }

# ==================== NOTIFICACIONES - RESUMEN ====================
@router.get("/notifications/summary")
async def get_notification_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get summary notifications for the point admin."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")
    from app.models import Request

    # Pending requests (last 24 hours)
    result = await db.execute(
        select(func.count(Request.id)).where(
            Request.exhibitor_id == exhibitor_id,
            Request.status == "pending",
            Request.created_at >= datetime.utcnow() - timedelta(hours=24)
        )
    )
    pending_24h = result.scalar()

    # Total available slots
    result = await db.execute(
        select(func.count(Slot.id)).where(
            Slot.exhibitor_id == exhibitor_id,
            Slot.status == "available"
        )
    )
    available_slots = result.scalar()

    # Slots about to expire (next 7 days)
    result = await db.execute(
        select(func.count(Slot.id)).where(
            Slot.exhibitor_id == exhibitor_id,
            Slot.date >= datetime.utcnow().date(),
            Slot.date <= (datetime.utcnow() + timedelta(days=7)).date(),
            Slot.status == "available"
        )
    )
    expiring_soon = result.scalar()

    return {
        "alerts": [
            {
                "type": "pending",
                "count": pending_24h or 0,
                "message": f"{pending_24h or 0} solicitudes pendientes en las últimas 24 horas"
            },
            {
                "type": "available",
                "count": available_slots or 0,
                "message": f"{available_slots or 0} turnos disponibles"
            },
            {
                "type": "expiring",
                "count": expiring_soon or 0,
                "message": f"{expiring_soon or 0} turnos próximos a vencer"
            }
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
