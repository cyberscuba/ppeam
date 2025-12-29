#!/usr/bin/env python3
"""Import hermanos from CSV file - Force mode (clears table first)"""
import sys
import os
import csv
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Hermano, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

def import_hermanos_from_csv_force(csv_file='usuarios.csv', clear_first=False):
    """Import hermanos from CSV file - optionally clear table first"""
    db = SessionLocal()
    
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', csv_file)
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return
        
        logger.info(f"Reading CSV file: {csv_path}")
        
        # Clear table if requested
        if clear_first:
            logger.warning("⚠️  CLEARING hermanos table first!")
            db.query(Hermano).delete()
            db.commit()
            logger.info("✓ Table cleared")
        
        imported = 0
        skipped = 0
        errors = 0
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    nombre = row.get('NOMBRE', '').strip()
                    congregacion = row.get('CONGREGACION', '').strip()
                    telefono = row.get('TELEFONO', '').strip()
                    
                    # Skip if no name or phone
                    if not nombre or not telefono:
                        logger.warning(f"Skipping row - missing name or phone: {row}")
                        skipped += 1
                        continue
                    
                    # Clean phone number - keep original format for hermanos
                    phone_clean = re.sub(r'\D', '', str(telefono))
                    if not phone_clean:
                        logger.warning(f"Invalid phone for {nombre}: {telefono}")
                        skipped += 1
                        continue
                    
                    # Check if hermano already exists (only if not clearing first)
                    if not clear_first:
                        existing = db.query(Hermano).filter(Hermano.telefono == telefono).first()
                        if existing:
                            logger.debug(f"Hermano already exists: {nombre} ({telefono})")
                            skipped += 1
                            continue
                    
                    # Create hermano
                    hermano = Hermano(
                        nombre=nombre,
                        congregacion=congregacion if congregacion else None,
                        telefono=telefono,
                        is_active=True
                    )
                    db.add(hermano)
                    db.flush()
                    
                    imported += 1
                    
                    if imported % 50 == 0:
                        logger.info(f"Imported {imported} hermanos...")
                        db.commit()
                
                except Exception as e:
                    logger.error(f"Error importing hermano {nombre}: {e}")
                    errors += 1
                    continue
        
        db.commit()
        
        logger.info("=" * 60)
        logger.info(f"✓ Import completed!")
        logger.info(f"  Imported: {imported} hermanos")
        logger.info(f"  Skipped: {skipped} hermanos (duplicates or invalid)")
        logger.info(f"  Errors: {errors}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during import: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Import hermanos from CSV')
    parser.add_argument('--force', action='store_true', help='Clear table before importing')
    args = parser.parse_args()
    
    logger.info("Starting hermanos import from CSV...")
    if args.force:
        logger.warning("⚠️  FORCE MODE: Will clear hermanos table first!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Cancelled")
            sys.exit(0)
    
    import_hermanos_from_csv_force(clear_first=args.force)
    logger.info("Import completed!")

