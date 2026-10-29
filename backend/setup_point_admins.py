#!/usr/bin/env python3
"""Setup point admins (Encargados Principal/Suplente for each exhibitor)."""

import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')
engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine)

# Import models
from app.models import Hermano, Admin, ExhibitorLeader, Exhibitor

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def setup_point_admins():
    """Create point admins for each exhibitor."""
    session = Session()

    try:
        # Get all exhibitors
        exhibitors = session.query(Exhibitor).all()
        print(f"\n📍 Total exhibidores encontrados: {len(exhibitors)}")

        # Sample data for point admins
        admin_data = [
            {"nombre": "Juan García", "rol": "principal"},
            {"nombre": "Carlos López", "rol": "suplente"},
        ]

        created_admins = []

        for exhibitor in exhibitors:
            print(f"\n🔧 Configurando: {exhibitor.name}")

            for idx, data in enumerate(admin_data):
                # Create hermano
                hermano_id = uuid.uuid4()
                position = "principal" if data["rol"] == "principal" else "suplente"
                exhibit_code = exhibitor.code.lower().replace('_', '')
                username = f"{exhibit_code}_{position}_{idx+1}"
                password = f"Admin@{exhibit_code}_{position}"

                hermano = Hermano(
                    id=hermano_id,
                    nombre=f"{data['nombre']} ({exhibitor.name})",
                    telefono=f"300{uuid.uuid4().int % 1000000:07d}",
                    congregacion="Portales",
                    genero="M"
                )
                session.add(hermano)
                session.flush()

                # Create admin user
                admin = Admin(
                    id=uuid.uuid4(),
                    username=username,
                    password_hash=hash_password(password),
                    role="point_admin"
                )
                session.add(admin)
                session.flush()

                # Link as exhibitor leader
                leader = ExhibitorLeader(
                    id=uuid.uuid4(),
                    admin_id=admin.id,
                    exhibitor_id=exhibitor.id,
                    position=position,
                    created_at=datetime.utcnow()
                )
                session.add(leader)

                created_admins.append({
                    "exhibitor": exhibitor.name,
                    "position": position,
                    "username": username,
                    "password": password,
                    "hermano": f"{data['nombre']} ({exhibitor.name})"
                })

                print(f"   ✅ {position.upper()}: {username}")

        session.commit()
        print(f"\n✅ Total admins creados: {len(created_admins)}")

        # Print credentials
        print("\n" + "=" * 70)
        print("📋 CREDENCIALES DE ADMINS POR PUNTO")
        print("=" * 70)
        for admin in created_admins:
            print(f"\n🏢 {admin['exhibitor']} - {admin['position'].upper()}")
            print(f"   Hermano: {admin['hermano']}")
            print(f"   Usuario: {admin['username']}")
            print(f"   Contraseña: {admin['password']}")

        print("\n" + "=" * 70)
        print("✅ Point admins configurados exitosamente")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    setup_point_admins()
