#!/usr/bin/env python3
"""Load initial data into the database synchronously."""

import os
import psycopg2
from uuid import uuid4

def load_data():
    """Load exhibitors and initial data."""
    db_url = os.getenv("DATABASE_URL", "")

    # Parse DATABASE_URL to get connection parameters
    # postgresql+asyncpg://user:pass@host:port/db
    if not db_url:
        # Fallback to env variables
        user = os.getenv("POSTGRES_USER", "exhibidores")
        password = os.getenv("POSTGRES_PASSWORD", "exhibidores123")
        host = os.getenv("DATABASE_HOST", "ppeam_postgres")
        port = os.getenv("DATABASE_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "exhibidores_db")
    else:
        # Parse URL: postgresql://exhibidores:exhibidores123@ppeam_postgres:5432/exhibidores_db
        import re
        match = re.match(r'postgresql(\+\w+)?://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if match:
            _, user, password, host, port, db = match.groups()
        else:
            print(f"❌ Invalid DATABASE_URL format: {db_url}")
            return

    try:
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=db,
            user=user,
            password=password
        )
        cursor = conn.cursor()

        print(f"✅ Conectado a {host}:{port}/{db}")

        # Check if exhibitors already exist
        cursor.execute("SELECT COUNT(*) FROM exhibitors")
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"✅ Base de datos ya contiene {count} exhibidores")
            cursor.close()
            conn.close()
            return

        print("📊 Cargando exhibidores...")

        # Insert exhibitors
        exhibitors_data = [
            {"code": "CUBA", "name": "Punto de Acopio Cuba"},
            {"code": "EL_LAGO", "name": "Punto de Acopio El Lago"},
            {"code": "BOLIVAR_Y_VICTORIA", "name": "Punto de Acopio Bolívar y Victoria"},
            {"code": "EL_PROGRESO", "name": "Punto de Acopio El Progreso"},
            {"code": "MEGACABLE", "name": "Punto de Acopio Megacable"},
            {"code": "LAS_ARAUCARIAS_Y_GALERIA", "name": "Punto de Acopio Las Araucarias y Galería"},
            {"code": "TERMINAL", "name": "Punto de Acopio Terminal"}
        ]

        for i, data in enumerate(exhibitors_data, 1):
            exhibitor_id = str(uuid4())
            cursor.execute("""
                INSERT INTO exhibitors (id, code, name, description, "order", is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
            """, (
                exhibitor_id,
                data['code'],
                data['name'],
                f"Punto de acopio {data['name']}",
                i,
                True
            ))
            print(f"  ✅ {data['name']}")

        conn.commit()
        print(f"\n✅ {len(exhibitors_data)} exhibidores cargados")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_data()
