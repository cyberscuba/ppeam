"""Point Admin (Encargado de Punto) endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from datetime import datetime, timedelta
from typing import List, Optional
import csv
from io import StringIO
from passlib.context import CryptContext

from app.database import get_db
from app.models import Admin, Exhibitor, Hermano, Request, RequestItem, Slot, ExhibitorLeader, AuditLog
from app.schemas import AdminLoginRequest, TokenResponse
from app.utils.security import create_access_token, get_current_user
from app.config import settings

router = APIRouter(prefix="/api/point-admin", tags=["Point Admin"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ==================== LOGIN ====================
@router.post("/login", response_model=TokenResponse)
async def point_admin_login(
    credentials: AdminLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login for point admins (username/password)."""

    # Get admin by username
    result = await db.execute(
        select(Admin).where(Admin.username == credentials.username)
    )
    admin = result.scalars().first()

    if not admin or admin.role != "point_admin":
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Verify password
    if not pwd_context.verify(credentials.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Get exhibitor leader info (point and position)
    result = await db.execute(
        select(ExhibitorLeader).where(ExhibitorLeader.admin_id == admin.id)
    )
    leader = result.scalars().first()

    if not leader:
        raise HTTPException(status_code=403, detail="No asignado a un punto")

    # Create token with exhibitor_id and position
    access_token = create_access_token(
        data={
            "sub": str(admin.id),
            "username": admin.username,
            "role": "point_admin",
            "exhibitor_id": str(leader.exhibitor_id),
            "position": leader.position
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(admin.id),
            "username": admin.username,
            "role": admin.role,
            "exhibitor_id": str(leader.exhibitor_id),
            "position": leader.position
        }
    }

# ==================== DASHBOARD ====================
@router.get("/dashboard")
async def get_point_dashboard(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard stats for the admin's point."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")

    # Get exhibitor name
    result = await db.execute(
        select(Exhibitor).where(Exhibitor.id == exhibitor_id)
    )
    exhibitor = result.scalars().first()

    if not exhibitor:
        raise HTTPException(status_code=404, detail="Punto no encontrado")

    # Count slots by status
    result = await db.execute(
        select(
            func.count(Slot.id).filter(Slot.status == "available"),
            func.count(Slot.id).filter(Slot.status == "taken"),
            func.count(Slot.id)
        ).where(Slot.exhibitor_id == exhibitor_id)
    )
    available, taken, total = result.first()

    # Count requests by status for this exhibitor
    result = await db.execute(
        select(
            func.count(Request.id).filter(Request.status == "approved"),
            func.count(Request.id).filter(Request.status == "cancelled")
        ).where(Request.exhibitor_id == exhibitor_id)
    )
    approved_requests, cancelled_requests = result.first()

    occupancy_percent = int((taken / total * 100) if total > 0 else 0)

    return {
        "exhibitor": {
            "id": str(exhibitor.id),
            "name": exhibitor.name,
            "code": exhibitor.code
        },
        "stats": {
            "total_slots": total or 0,
            "available_slots": available or 0,
            "taken_slots": taken or 0,
            "occupancy_percent": occupancy_percent,
            "approved_requests": approved_requests or 0,
            "cancelled_requests": cancelled_requests or 0
        },
        "updated_at": datetime.utcnow().isoformat()
    }

# ==================== REQUESTS (Hermanos que solicitaron) ====================
@router.get("/requests")
async def get_point_requests(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, cancelled"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get requests for this point (hermanos that requested turns)."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")

    # Build query
    query = select(Request).where(Request.exhibitor_id == exhibitor_id)

    if status:
        query = query.where(Request.status == status)

    # Count total
    count_result = await db.execute(
        select(func.count(Request.id)).where(Request.exhibitor_id == exhibitor_id)
    )
    total = count_result.scalar()

    # Paginate
    query = query.order_by(desc(Request.created_at))
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    requests = result.scalars().all()

    # Format response
    data = []
    for req in requests:
        # Get hermano info
        hermano_result = await db.execute(
            select(Hermano).where(Hermano.id == req.hermano_id)
        )
        hermano = hermano_result.scalars().first()

        # Get request items (turnos solicitados)
        items_result = await db.execute(
            select(RequestItem).where(RequestItem.request_id == req.id)
        )
        items = items_result.scalars().all()

        data.append({
            "id": str(req.id),
            "hermano": {
                "id": str(hermano.id),
                "nombre": hermano.nombre,
                "telefono": hermano.telefono,
                "congregacion": hermano.congregacion
            },
            "status": req.status,
            "turns_requested": len(items),
            "created_at": req.created_at.isoformat(),
            "turns": [
                {
                    "id": str(item.id),
                    "schedule_id": str(item.schedule_id),
                    "status": item.status,
                    "date": item.date.isoformat() if item.date else None
                }
                for item in items
            ]
        })

    return {
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }

# ==================== LIBERAR TURNO ====================
@router.post("/release-turn/{request_item_id}")
async def release_turn(
    request_item_id: str,
    reason: str = Query(..., description="Razón por la que se libera el turno"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Release a turn (mark as available again)."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")
    admin_id = current_user.get("sub")

    # Get request item
    result = await db.execute(
        select(RequestItem).where(RequestItem.id == request_item_id)
    )
    request_item = result.scalars().first()

    if not request_item:
        raise HTTPException(status_code=404, detail="Turno no encontrado")

    # Get request and verify it's for this exhibitor
    result = await db.execute(
        select(Request).where(Request.id == request_item.request_id)
    )
    request = result.scalars().first()

    if str(request.exhibitor_id) != str(exhibitor_id):
        raise HTTPException(status_code=403, detail="No autorizado para este punto")

    # Update request_item status to available
    request_item.status = "available"

    # Update slot status to available
    result = await db.execute(
        select(Slot).where(Slot.id == request_item.slot_id)
    )
    slot = result.scalars().first()
    if slot:
        slot.status = "available"

    # Create audit log
    audit = AuditLog(
        admin_id=admin_id,
        action="release_turn",
        entity_type="request_item",
        entity_id=request_item_id,
        details={
            "reason": reason,
            "exhibitor_id": str(exhibitor_id),
            "position": current_user.get("position")
        }
    )
    db.add(audit)

    await db.commit()

    return {
        "message": "Turno liberado exitosamente",
        "request_item_id": request_item_id,
        "status": "available"
    }

# ==================== HERMANOS QUE SOLICITARON ====================
@router.get("/hermanos-request-list")
async def get_hermanos_request_list(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of hermanos who requested turns for this point."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")

    # Get unique hermanos with requests for this exhibitor
    query = select(
        Hermano,
        func.count(Request.id).label("request_count")
    ).join(
        Request, Hermano.id == Request.hermano_id
    ).where(
        Request.exhibitor_id == exhibitor_id
    ).group_by(
        Hermano.id
    ).order_by(
        desc("request_count"), Hermano.nombre
    )

    # Count total
    count_result = await db.execute(
        select(func.count(func.distinct(Request.hermano_id))).where(
            Request.exhibitor_id == exhibitor_id
        )
    )
    total = count_result.scalar()

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    hermanos_data = result.all()

    data = [
        {
            "id": str(h.id),
            "nombre": h.nombre,
            "telefono": h.telefono,
            "congregacion": h.congregacion,
            "genero": h.genero,
            "request_count": count
        }
        for h, count in hermanos_data
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

# ==================== EXPORT ====================
@router.get("/export", response_class=None)
async def export_data(
    format: str = Query("csv", regex="^(csv|json)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export point data in CSV or JSON format."""

    if current_user.get("role") != "point_admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")

    exhibitor_id = current_user.get("exhibitor_id")

    # Get all data for this point
    result = await db.execute(
        select(Request).where(Request.exhibitor_id == exhibitor_id)
    )
    requests = result.scalars().all()

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)

        # Headers
        writer.writerow([
            "Hermano",
            "Teléfono",
            "Congregación",
            "Estado",
            "Turnos Solicitados",
            "Fecha Solicitud"
        ])

        # Data
        for req in requests:
            hermano_result = await db.execute(
                select(Hermano).where(Hermano.id == req.hermano_id)
            )
            hermano = hermano_result.scalars().first()

            items_result = await db.execute(
                select(RequestItem).where(RequestItem.request_id == req.id)
            )
            items = items_result.scalars().all()

            writer.writerow([
                hermano.nombre,
                hermano.telefono,
                hermano.congregacion,
                req.status,
                len(items),
                req.created_at.strftime("%Y-%m-%d %H:%M")
            ])

        return {
            "content": output.getvalue(),
            "filename": f"punto_{exhibitor_id}_{datetime.utcnow().strftime('%Y%m%d')}.csv",
            "media_type": "text/csv"
        }

    else:  # JSON
        data = []
        for req in requests:
            hermano_result = await db.execute(
                select(Hermano).where(Hermano.id == req.hermano_id)
            )
            hermano = hermano_result.scalars().first()

            items_result = await db.execute(
                select(RequestItem).where(RequestItem.request_id == req.id)
            )
            items = items_result.scalars().all()

            data.append({
                "hermano": {
                    "nombre": hermano.nombre,
                    "telefono": hermano.telefono,
                    "congregacion": hermano.congregacion
                },
                "status": req.status,
                "turns": len(items),
                "created_at": req.created_at.isoformat()
            })

        return {
            "data": data,
            "exported_at": datetime.utcnow().isoformat(),
            "point_id": str(exhibitor_id)
        }
