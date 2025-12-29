#!/usr/bin/env python3
"""Import horarios from horariosPuntoExibidor.json"""
import sys
import os
import json
from datetime import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Exhibitor, Schedule
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

# Mapeo de días de la semana en español a números (0=Lunes, 6=Domingo)
DIAS_SEMANA = {
    "Lunes": 0,
    "Martes": 1,
    "Miércoles": 2,
    "Miercoles": 2,  # Sin tilde
    "Jueves": 3,
    "Viernes": 4,
    "Sábado": 5,
    "Sabado": 5,  # Sin tilde
    "Domingo": 6,
    "Festivos": None  # Los festivos no tienen weekday específico
}

def find_exhibitor_by_name(db, name_pattern):
    """Find exhibitor by name (case insensitive, partial match)"""
    exhibitors = db.query(Exhibitor).filter(
        Exhibitor.name.ilike(f"%{name_pattern}%")
    ).all()
    
    if len(exhibitors) == 1:
        return exhibitors[0]
    elif len(exhibitors) > 1:
        logger.warning(f"Multiple exhibitors found for '{name_pattern}': {[e.name for e in exhibitors]}")
        return exhibitors[0]  # Return first match
    else:
        logger.warning(f"No exhibitor found for '{name_pattern}'")
        return None

def parse_time(time_str):
    """Parse time string (HH:MM) to time object"""
    try:
        parts = time_str.split(':')
        if len(parts) == 2:
            return time(int(parts[0]), int(parts[1]))
        elif len(parts) == 3:
            return time(int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            raise ValueError(f"Invalid time format: {time_str}")
    except Exception as e:
        logger.error(f"Error parsing time '{time_str}': {e}")
        return None

def import_horarios(json_file='horariosPuntoExibidor.json', clear_existing=False):
    """Import horarios from horariosPuntoExibidor.json"""
    db = SessionLocal()
    
    try:
        # Buscar el archivo JSON en la raíz del proyecto o en /app
        json_path = os.path.join(os.path.dirname(__file__), '..', '..', json_file)
        if not os.path.exists(json_path):
            # Intentar en /app (dentro del contenedor)
            json_path = os.path.join('/app', json_file)
        
        if not os.path.exists(json_path):
            logger.error(f"JSON file not found: {json_path}")
            return
        
        logger.info(f"Reading JSON file: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        horarios = data.get('horarios', {})
        
        created_schedules = 0
        skipped_schedules = 0
        errors = 0
        
        # Si clear_existing, eliminar schedules existentes
        if clear_existing:
            logger.warning("⚠️  CLEARING existing schedules!")
            db.query(Schedule).delete()
            db.commit()
            logger.info("✓ Schedules cleared")
        
        # Procesar cada punto
        for punto_name, dias_data in horarios.items():
            logger.info(f"\nProcessing punto: {punto_name}")
            
            # Buscar exhibitor
            exhibitor = find_exhibitor_by_name(db, punto_name)
            if not exhibitor:
                logger.warning(f"Exhibitor not found for '{punto_name}', skipping...")
                errors += 1
                continue
            
            logger.info(f"Found exhibitor: {exhibitor.name} (ID: {exhibitor.id})")
            
            # Procesar cada día
            for dia_name, horarios_list in dias_data.items():
                weekday = DIAS_SEMANA.get(dia_name)
                
                if weekday is None and dia_name != "Festivos":
                    logger.warning(f"Unknown day: {dia_name}, skipping...")
                    continue
                
                # Procesar cada horario del día
                for horario in horarios_list:
                    inicio_str = horario.get('inicio')
                    fin_str = horario.get('fin')
                    
                    if not inicio_str or not fin_str:
                        logger.warning(f"Invalid horario format: {horario}")
                        continue
                    
                    start_time = parse_time(inicio_str)
                    end_time = parse_time(fin_str)
                    
                    if not start_time or not end_time:
                        logger.warning(f"Could not parse times: {inicio_str} - {fin_str}")
                        continue
                    
                    # Verificar si ya existe este schedule
                    existing = db.query(Schedule).filter(
                        Schedule.exhibitor_id == exhibitor.id,
                        Schedule.weekday == weekday,
                        Schedule.start_time == start_time,
                        Schedule.end_time == end_time
                    ).first()
                    
                    if existing:
                        logger.debug(f"Schedule already exists: {exhibitor.name} - {dia_name} {inicio_str}-{fin_str}")
                        skipped_schedules += 1
                        continue
                    
                    # Crear nuevo schedule
                    schedule = Schedule(
                        exhibitor_id=exhibitor.id,
                        weekday=weekday,
                        start_time=start_time,
                        end_time=end_time,
                        is_active=True
                    )
                    db.add(schedule)
                    db.flush()
                    created_schedules += 1
                    logger.info(f"Created schedule: {exhibitor.name} - {dia_name} {inicio_str}-{fin_str}")
        
        db.commit()
        
        logger.info("=" * 60)
        logger.info(f"✓ Import completed!")
        logger.info(f"  Created schedules: {created_schedules}")
        logger.info(f"  Skipped (duplicates): {skipped_schedules}")
        logger.info(f"  Errors: {errors}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during import: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Import horarios from JSON')
    parser.add_argument('--clear', action='store_true', help='Clear existing schedules before importing')
    args = parser.parse_args()
    
    logger.info("Starting horarios import...")
    if args.clear:
        logger.warning("⚠️  CLEAR MODE: Will clear existing schedules first!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Cancelled")
            sys.exit(0)
    
    import_horarios(clear_existing=args.clear)
    logger.info("Import completed!")

