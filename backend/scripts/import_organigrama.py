#!/usr/bin/env python3
"""Import usuarios/hermanos from organigrama.json and create exhibitor leaders"""
import sys
import os
import json
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Hermano, User, Admin, Exhibitor, ExhibitorLeader
from passlib.context import CryptContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sync database
sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

# Mapeo de nombres de puntos del organigrama a nombres de exhibitors
PUNTO_MAPPING = {
    "CUBA": ["Cuba"],
    "EL_LAGO": ["El Lago (Dos Quebradas)"],
    "BOLIVAR_Y_VICTORIA": ["Plaza Bolivar", "Ciudad Victoria"],
    "EL_PROGRESO": ["El Progreso (Dos Quebradas)"],
    "MEGACABLE": ["Olaya Megacable"],
    "LAS_ARAUCARIAS_Y_GALERIA": ["Parque Las Araucarias (Santa Rosa)", "Galerías (Santa Rosa)"],
    "TERMINAL": ["Terminal"]
}

def find_or_create_hermano(db, nombre, telefono=None):
    """Find or create hermano by name"""
    # Buscar por nombre exacto
    hermano = db.query(Hermano).filter(Hermano.nombre == nombre).first()
    
    if not hermano:
        # Si no existe, crear uno nuevo (sin teléfono si no se proporciona)
        hermano = Hermano(
            nombre=nombre,
            telefono=telefono or f"TEMP_{nombre.replace(' ', '_')}",
            is_active=True
        )
        db.add(hermano)
        db.flush()
        logger.info(f"Created hermano: {nombre}")
    
    return hermano

def find_or_create_user(db, nombre, telefono=None):
    """Find or create user by name"""
    # Buscar por nombre exacto
    user = db.query(User).filter(User.full_name == nombre).first()
    
    if not user:
        # Si no existe, crear uno nuevo
        phone = telefono or f"+57TEMP{nombre.replace(' ', '')[:10]}"
        user = User(
            full_name=nombre,
            phone=phone,
            is_active=True
        )
        db.add(user)
        db.flush()
        logger.info(f"Created user: {nombre}")
    
    return user

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

def create_admin_for_hermano(db, hermano, role="lider_exhibidor"):
    """Create admin account for hermano if doesn't exist"""
    existing_admin = db.query(Admin).filter(Admin.hermano_id == hermano.id).first()
    
    if existing_admin:
        # Update role if needed
        if existing_admin.role != role:
            existing_admin.role = role
            db.flush()
            logger.info(f"Updated admin role for {hermano.nombre} to {role}")
        return existing_admin
    
    # Create username from nombre
    username = hermano.nombre.lower().replace(' ', '_').replace('.', '').replace(',', '')
    # Check if username exists
    counter = 1
    base_username = username
    while db.query(Admin).filter(Admin.username == username).first():
        username = f"{base_username}_{counter}"
        counter += 1
    
    # Default password (should be changed)
    password_hash = pwd_context.hash("cambiar123")
    
    admin = Admin(
        hermano_id=hermano.id,
        username=username,
        password_hash=password_hash,
        role=role
    )
    db.add(admin)
    db.flush()
    logger.info(f"Created admin for {hermano.nombre} (username: {username}, password: cambiar123)")
    
    return admin

def import_organigrama(json_file='organigrama.json'):
    """Import usuarios from organigrama.json and create exhibitor leaders"""
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
        
        organigrama = data.get('organigrama_ppeam', {})
        puntos = organigrama.get('puntos', {})
        
        imported_hermanos = 0
        created_admins = 0
        created_leaders = 0
        errors = 0
        
        # Procesar cada punto
        for punto_key, punto_data in puntos.items():
            logger.info(f"\nProcessing punto: {punto_key}")
            
            # Obtener nombres de exhibitors para este punto
            exhibitor_names = PUNTO_MAPPING.get(punto_key, [])
            
            if not exhibitor_names:
                logger.warning(f"No exhibitor mapping found for {punto_key}")
                continue
            
            # Commit después de cada punto para evitar problemas de transacción
            try:
                db.commit()
            except Exception as e:
                logger.warning(f"Error committing after punto {punto_key}: {e}")
                db.rollback()
            
            # Procesar ENCARGADO (líder principal)
            encargado_nombre = punto_data.get('ENCARGADO')
            if encargado_nombre:
                try:
                    # Check if hermano exists before creating
                    existing_hermano = db.query(Hermano).filter(Hermano.nombre == encargado_nombre).first()
                    if not existing_hermano:
                        imported_hermanos += 1
                    
                    hermano = find_or_create_hermano(db, encargado_nombre)
                    
                    admin = create_admin_for_hermano(db, hermano, role="lider_exhibidor")
                    if admin.id not in [a.id for a in db.query(Admin).all() if a.id == admin.id]:
                        created_admins += 1
                    
                    # Asignar como líder principal a todos los exhibitors de este punto
                    for exhibitor_name in exhibitor_names:
                        exhibitor = find_exhibitor_by_name(db, exhibitor_name)
                        if exhibitor:
                            # Verificar si ya existe un líder principal
                            existing_principal = db.query(ExhibitorLeader).filter(
                                ExhibitorLeader.exhibitor_id == exhibitor.id,
                                ExhibitorLeader.position == "principal"
                            ).first()
                            
                            if existing_principal:
                                if existing_principal.admin_id != admin.id:
                                    logger.info(f"Updating principal leader for {exhibitor.name} to {encargado_nombre}")
                                    existing_principal.admin_id = admin.id
                                    db.flush()
                            else:
                                # Verificar que no esté ya asignado
                                existing = db.query(ExhibitorLeader).filter(
                                    ExhibitorLeader.admin_id == admin.id,
                                    ExhibitorLeader.exhibitor_id == exhibitor.id
                                ).first()
                                
                                if not existing:
                                    leader = ExhibitorLeader(
                                        admin_id=admin.id,
                                        exhibitor_id=exhibitor.id,
                                        position="principal"
                                    )
                                    db.add(leader)
                                    db.flush()
                                    created_leaders += 1
                                    logger.info(f"Created principal leader: {encargado_nombre} -> {exhibitor.name}")
                        else:
                            logger.warning(f"Exhibitor not found: {exhibitor_name}")
                    
                    # Commit después de cada asignación exitosa
                    try:
                        db.commit()
                    except Exception as e:
                        logger.warning(f"Error committing leader assignment: {e}")
                        db.rollback()
                    
                except Exception as e:
                    logger.error(f"Error processing ENCARGADO {encargado_nombre}: {e}")
                    db.rollback()  # Rollback para limpiar la transacción
                    errors += 1
                    continue
            
            # Procesar TURNOS (líder suplente)
            turnos_nombre = punto_data.get('TURNOS')
            if turnos_nombre:
                try:
                    # Check if hermano exists before creating
                    existing_hermano = db.query(Hermano).filter(Hermano.nombre == turnos_nombre).first()
                    if not existing_hermano:
                        imported_hermanos += 1
                    
                    hermano = find_or_create_hermano(db, turnos_nombre)
                    
                    # Check if admin exists before creating
                    existing_admin = db.query(Admin).filter(Admin.hermano_id == hermano.id).first()
                    if not existing_admin:
                        created_admins += 1
                    
                    admin = create_admin_for_hermano(db, hermano, role="lider_exhibidor")
                    
                    # Asignar como líder suplente a todos los exhibitors de este punto
                    for exhibitor_name in exhibitor_names:
                        exhibitor = find_exhibitor_by_name(db, exhibitor_name)
                        if exhibitor:
                            # Verificar que no esté ya asignado
                            existing = db.query(ExhibitorLeader).filter(
                                ExhibitorLeader.admin_id == admin.id,
                                ExhibitorLeader.exhibitor_id == exhibitor.id
                            ).first()
                            
                            if not existing:
                                leader = ExhibitorLeader(
                                    admin_id=admin.id,
                                    exhibitor_id=exhibitor.id,
                                    position="suplente"
                                )
                                db.add(leader)
                                db.flush()
                                created_leaders += 1
                                logger.info(f"Created suplente leader: {turnos_nombre} -> {exhibitor.name}")
                        else:
                            logger.warning(f"Exhibitor not found: {exhibitor_name}")
                    
                    # Commit después de cada asignación exitosa
                    try:
                        db.commit()
                    except Exception as e:
                        logger.warning(f"Error committing leader assignment: {e}")
                        db.rollback()
                    
                except Exception as e:
                    logger.error(f"Error processing TURNOS {turnos_nombre}: {e}")
                    db.rollback()  # Rollback para limpiar la transacción
                    errors += 1
                    continue
        
        # Último commit
        try:
            db.commit()
        except Exception as e:
            logger.warning(f"Error en commit final: {e}")
            db.rollback()
        
        logger.info("=" * 60)
        logger.info(f"✓ Import completed!")
        logger.info(f"  Imported/Found hermanos: {imported_hermanos}")
        logger.info(f"  Created admins: {created_admins}")
        logger.info(f"  Created leader assignments: {created_leaders}")
        logger.info(f"  Errors: {errors}")
        logger.info("=" * 60)
        logger.info("\n⚠️  IMPORTANTE: Las contraseñas por defecto son 'cambiar123'")
        logger.info("   Por favor, cambia las contraseñas después del primer login.")
        
    except Exception as e:
        logger.error(f"Error during import: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting organigrama import...")
    import_organigrama()
    logger.info("Import completed!")

