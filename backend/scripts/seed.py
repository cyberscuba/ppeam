#!/usr/bin/env python3
"""Seed script for PPEAM Pereira - Predicación Pública Especial Áreas Metropolitanas"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Point, Schedule, User, Admin
from datetime import time
from passlib.context import CryptContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

def seed_points():
    """Create PPEAM Pereira exhibition points"""
    db = SessionLocal()
    
    try:
        # Check if points already exist
        existing = db.query(Point).count()
        if existing > 0:
            logger.info(f"Points already exist ({existing}). Skipping seed.")
            return
        
        logger.info("Creating PPEAM Pereira points...")
        
        # Real exhibition points in Pereira and surrounding areas
        points_data = [
            {"code": "GALE-SR", "name": "Galería - Sta Rosa", "description": "Galería de Santa Rosa de Cabal"},
            {"code": "ARAU-SR", "name": "Parque las Araucarias - Sta Rosa", "description": "Parque las Araucarias, Santa Rosa de Cabal"},
            {"code": "PROG-DD", "name": "El Progreso - Ddas", "description": "El Progreso, Dosquebradas"},
            {"code": "LAGO-DD", "name": "El Lago - Ddas", "description": "El Lago, Dosquebradas"},
            {"code": "BOLI", "name": "Parque Bolívar", "description": "Parque Bolívar, Pereira"},
            {"code": "VICT", "name": "Parque Victoria", "description": "Parque Victoria, Pereira"},
            {"code": "MEGA", "name": "Megacable", "description": "Estación Megacable, Pereira"},
            {"code": "TERM", "name": "Terminal", "description": "Terminal de Transportes, Pereira"},
            {"code": "CUBA", "name": "Parque de Cuba", "description": "Parque de Cuba, Pereira"},
        ]
        
        # Coordinates for Pereira area
        base_lat = 4.8133
        base_lon = -75.6961
        
        for i, point_data in enumerate(points_data):
            point = Point(
                code=point_data["code"],
                name=point_data["name"],
                description=point_data["description"],
                latitude=base_lat + (i * 0.001),
                longitude=base_lon + (i * 0.001),
                is_active=True
            )
            db.add(point)
            db.flush()
            
            # Create 4 schedules per point (morning, afternoon, evening, night)
            schedules = [
                {"weekday": None, "start": time(8, 0), "end": time(12, 0)},   # Mañana
                {"weekday": None, "start": time(12, 0), "end": time(16, 0)},  # Tarde
                {"weekday": None, "start": time(16, 0), "end": time(20, 0)},  # Noche
                {"weekday": None, "start": time(20, 0), "end": time(22, 0)},  # Noche tardía
            ]
            
            for sched in schedules:
                schedule = Schedule(
                    point_id=point.id,
                    weekday=sched["weekday"],
                    start_time=sched["start"],
                    end_time=sched["end"],
                    is_active=True
                )
                db.add(schedule)
            
            logger.info(f"Created point: {point.name}")
        
        db.commit()
        logger.info(f"✓ Successfully created {len(points_data)} PPEAM Pereira points")
        
    except Exception as e:
        logger.error(f"Error seeding points: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def seed_admin():
    """Create default admin users"""
    db = SessionLocal()
    
    try:
        # Check if admin exists
        existing = db.query(Admin).count()
        if existing > 0:
            logger.info("Admins already exist. Skipping.")
            return
        
        logger.info("Creating admin users...")
        
        # Admin users (they can also make requests as regular users)
        admins_data = [
            {
                "full_name": "Coordinador PPEAM",
                "phone": "+573001234567",
                "email": "coordinador@ppeam.com",
                "username": "admin",
                "password": "admin123",
                "role": "coordinador"
            },
            {
                "full_name": "Supervisor PPEAM",
                "phone": "+573007654321",
                "email": "supervisor@ppeam.com",
                "username": "supervisor",
                "password": "super123",
                "role": "supervisor"
            }
        ]
        
        for admin_data in admins_data:
            # Create user (admin can also make requests)
            user = User(
                full_name=admin_data["full_name"],
                phone=admin_data["phone"],
                email=admin_data["email"],
                is_active=True
            )
            db.add(user)
            db.flush()
            
            # Create admin with username/password
            password_hash = pwd_context.hash(admin_data["password"])
            admin = Admin(
                user_id=user.id,
                username=admin_data["username"],
                password_hash=password_hash,
                role=admin_data["role"]
            )
            db.add(admin)
            
            logger.info(f"✓ Admin created: {admin_data['username']} (password: {admin_data['password']})")
        
        db.commit()
        logger.info("✓ Admin users created successfully")
        
    except Exception as e:
        logger.error(f"Error creating admins: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting PPEAM Pereira seed process...")
    seed_points()
    seed_admin()
    logger.info("Seed completed!")
