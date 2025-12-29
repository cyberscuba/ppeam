#!/usr/bin/env python3
"""Ensure admin users exist with correct passwords"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Admin, User
from passlib.context import CryptContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

def ensure_admins():
    """Create or update admin users"""
    db = SessionLocal()
    
    try:
        admins_data = [
            {
                "full_name": "Coordinador PPEAM",
                "phone": "+573001234567",
                "email": "coordinador@ppeam.com",
                "username": "admin",
                "password": "admin123",
                "role": "super_admin"
            },
            {
                "full_name": "Supervisor PPEAM",
                "phone": "+573007654321",
                "email": "supervisor@ppeam.com",
                "username": "supervisor",
                "password": "super123",
                "role": "super_admin"
            }
        ]
        
        for admin_data in admins_data:
            # Check if admin exists
            existing_admin = db.query(Admin).filter(Admin.username == admin_data["username"]).first()
            
            if existing_admin:
                # Update password
                password_hash = pwd_context.hash(admin_data["password"])
                existing_admin.password_hash = password_hash
                
                # Ensure user is active
                if existing_admin.user_id:
                    user = db.query(User).filter(User.id == existing_admin.user_id).first()
                    if user:
                        user.is_active = True
                        logger.info(f"✓ Updated admin: {admin_data['username']} (password reset)")
                    else:
                        logger.warning(f"⚠ Admin {admin_data['username']} has no associated user")
                else:
                    logger.warning(f"⚠ Admin {admin_data['username']} has no user_id")
            else:
                # Create new admin
                logger.info(f"Creating admin: {admin_data['username']}...")
                
                # Check if user exists
                user = db.query(User).filter(User.phone == admin_data["phone"]).first()
                
                if not user:
                    # Create user
                    user = User(
                        full_name=admin_data["full_name"],
                        phone=admin_data["phone"],
                        email=admin_data["email"],
                        is_active=True
                    )
                    db.add(user)
                    db.flush()
                    logger.info(f"  Created user: {admin_data['full_name']}")
                else:
                    # Update existing user
                    user.full_name = admin_data["full_name"]
                    user.email = admin_data["email"]
                    user.is_active = True
                    logger.info(f"  Updated user: {admin_data['full_name']}")
                
                # Create admin
                password_hash = pwd_context.hash(admin_data["password"])
                admin = Admin(
                    user_id=user.id,
                    username=admin_data["username"],
                    password_hash=password_hash,
                    role=admin_data["role"]
                )
                db.add(admin)
                logger.info(f"✓ Created admin: {admin_data['username']} (password: {admin_data['password']})")
        
        db.commit()
        logger.info("✓ All admins ensured successfully")
        
        # List all admins
        all_admins = db.query(Admin).all()
        logger.info("\n=== Current Admins ===")
        for admin in all_admins:
            user = db.query(User).filter(User.id == admin.user_id).first() if admin.user_id else None
            status = "✓ Active" if (user and user.is_active) else "✗ Inactive"
            logger.info(f"  {admin.username} ({admin.role}) - {status}")
            if user:
                logger.info(f"    User: {user.full_name} - {user.phone} - Active: {user.is_active}")
        
    except Exception as e:
        logger.error(f"Error ensuring admins: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Ensuring admin users exist...")
    ensure_admins()
    logger.info("Done!")

