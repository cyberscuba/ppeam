#!/usr/bin/env python3
"""Check hermanos table status"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Hermano
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

def check_hermanos():
    """Check hermanos table"""
    db = SessionLocal()
    
    try:
        total = db.query(Hermano).count()
        active = db.query(Hermano).filter(Hermano.is_active == True).count()
        inactive = db.query(Hermano).filter(Hermano.is_active == False).count()
        
        logger.info("=" * 60)
        logger.info("HERMANOS TABLE STATUS")
        logger.info("=" * 60)
        logger.info(f"Total hermanos: {total}")
        logger.info(f"Active: {active}")
        logger.info(f"Inactive: {inactive}")
        
        if total > 0:
            # Show first 5
            hermanos = db.query(Hermano).limit(5).all()
            logger.info("\nFirst 5 hermanos:")
            for h in hermanos:
                logger.info(f"  - {h.nombre} ({h.telefono}) - {h.congregacion or 'N/A'}")
        else:
            logger.info("\n⚠️  Table is empty!")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error checking hermanos: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    check_hermanos()

