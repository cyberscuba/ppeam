#!/usr/bin/env python3
"""Reset admin passwords"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Admin
from passlib.context import CryptContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

def reset_passwords():
    """Reset admin passwords"""
    db = SessionLocal()
    
    try:
        # Update admin password
        admin_hash = pwd_context.hash("admin123")
        db.execute(
            update(Admin).where(Admin.username == "admin").values(password_hash=admin_hash)
        )
        logger.info("✓ Password reset for admin: admin123")
        
        # Update supervisor password
        super_hash = pwd_context.hash("super123")
        db.execute(
            update(Admin).where(Admin.username == "supervisor").values(password_hash=super_hash)
        )
        logger.info("✓ Password reset for supervisor: super123")
        
        db.commit()
        logger.info("✓ All passwords reset successfully")
        
    except Exception as e:
        logger.error(f"Error resetting passwords: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Resetting admin passwords...")
    reset_passwords()
    logger.info("Done!")
