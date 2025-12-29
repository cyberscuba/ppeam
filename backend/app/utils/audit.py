from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditLog
from typing import Optional, Dict, Any
from uuid import UUID

async def log_audit(
    db: AsyncSession,
    actor_id: Optional[UUID],
    actor_type: str,
    action: str,
    target: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log audit event"""
    try:
        audit = AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            target=target,
            meta=meta or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit)
        await db.commit()
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        await db.rollback()
        # Log error but don't raise - audit is non-critical
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to log audit event: {e}")
