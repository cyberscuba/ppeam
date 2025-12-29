#!/usr/bin/env python3
"""Import hermanos from CSV file"""
import sys
import os
import csv
import re
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

def clean_phone(phone):
    """Clean and format phone number to E.164 format"""
    if not phone:
        return None
    
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', str(phone))
    
    # Skip if empty after cleaning
    if not phone:
        return None
    
    # Add Colombia country code if not present
    if len(phone) == 10:
        phone = '57' + phone
    elif len(phone) == 7:
        # Landline, add Pereira area code
        phone = '576' + phone
    
    # Add + prefix
    if not phone.startswith('+'):
        phone = '+' + phone
    
    return phone

def import_hermanos_from_csv(csv_file='usuarios.csv'):
    """Import hermanos from CSV file"""
    db = SessionLocal()
    
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', csv_file)
        
        if not os.path.exists(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return
        
        logger.info(f"Reading CSV file: {csv_path}")
        
        imported = 0
        skipped = 0
        errors = 0
        
        # Open with utf-8-sig to handle BOM
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    # Get values, handling BOM in keys and cleaning whitespace
                    nombre = row.get('NOMBRE', row.get('\ufeffNOMBRE', '')).strip()
                    congregacion = row.get('CONGREGACION', '').strip()
                    telefono = row.get('TELEFONO', '').strip()
                    
                    # Skip if no name or phone
                    if not nombre or not telefono:
                        logger.warning(f"Skipping row - missing name or phone: nombre='{nombre}', telefono='{telefono}'")
                        skipped += 1
                        continue
                    
                    # Clean phone number - remove all non-digits for validation
                    phone_clean = re.sub(r'\D', '', str(telefono))
                    if not phone_clean or len(phone_clean) < 7:
                        logger.warning(f"Invalid phone for {nombre}: {telefono} (cleaned: {phone_clean})")
                        skipped += 1
                        continue
                    
                    # Normalize phone for storage (keep original format but clean spaces)
                    # Some phones have multiple numbers separated by - or spaces
                    telefono_normalized = telefono.strip()
                    
                    # Truncate if too long (max 50 chars)
                    if len(telefono_normalized) > 50:
                        logger.warning(f"Phone too long for {nombre}: {telefono_normalized[:50]}... (truncated)")
                        telefono_normalized = telefono_normalized[:50]
                    
                    # Check if hermano already exists by telefono
                    existing = db.query(Hermano).filter(Hermano.telefono == telefono_normalized).first()
                    if existing:
                        logger.debug(f"Hermano already exists: {nombre} ({telefono_normalized})")
                        skipped += 1
                        continue
                    
                    # Create hermano
                    hermano = Hermano(
                        nombre=nombre,
                        congregacion=congregacion if congregacion else None,
                        telefono=telefono_normalized,
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
                    db.rollback()  # Rollback to continue with next record
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
    logger.info("Starting hermanos import from CSV...")
    import_hermanos_from_csv()
    logger.info("Import completed!")
