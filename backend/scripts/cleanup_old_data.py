#!/usr/bin/env python3
"""Cleanup old data based on retention policy"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Request, OTPCode, AuditLog, Notification, AppSetting
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

def cleanup():
    """Delete old data based on retention policy"""
    db = SessionLocal()
    
    try:
        # Get retention settings
        result = db.execute(
            select(AppSetting).where(AppSetting.key == "data_retention")
        ).scalar_one_or_none()
        
        retention_days = result.value.get("days", 365) if result else 365
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        logger.info(f"Cleaning data older than {retention_days} days ({cutoff_date})")
        
        # Delete old OTP codes
        otp_deleted = db.execute(
            delete(OTPCode).where(OTPCode.created_at < cutoff_date)
        ).rowcount
        logger.info(f"Deleted {otp_deleted} old OTP codes")
        
        # Delete old audit logs
        audit_deleted = db.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        ).rowcount
        logger.info(f"Deleted {audit_deleted} old audit logs")
        
        # Delete old notifications
        notif_deleted = db.execute(
            delete(Notification).where(Notification.created_at < cutoff_date)
        ).rowcount
        logger.info(f"Deleted {notif_deleted} old notifications")
        
        db.commit()
        logger.info("✓ Cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup()
