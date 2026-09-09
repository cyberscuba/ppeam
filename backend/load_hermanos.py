#!/usr/bin/env python3
"""Load hermanos from CSV into database."""

import os
import csv
import psycopg2
from uuid import uuid4

def load_hermanos():
    """Load hermanos from CSV file."""
    # Get database connection parameters
    user = os.getenv("POSTGRES_USER", "exhibidores")
    password = os.getenv("POSTGRES_PASSWORD", "exhibidores123")
    host = os.getenv("DATABASE_HOST", "ppeam_postgres")
    port = os.getenv("DATABASE_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "exhibidores_db")

    csv_file = "/app/ListadoHermanosMetropolitana.csv"

    try:
        if not os.path.exists(csv_file):
            print(f"❌ CSV file not found: {csv_file}")
            return

        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=db,
            user=user,
            password=password
        )
        cursor = conn.cursor()

        print(f"✅ Conectado a {host}:{port}/{db}")

        # Check if hermanos already exist
        cursor.execute("SELECT COUNT(*) FROM hermanos")
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"✅ Base de datos ya contiene {count} hermanos")
            cursor.close()
            conn.close()
            return

        print("📥 Leyendo archivo CSV...")
        hermanos_data = []
        seen_phones = set()

        with open(csv_file, 'r', encoding='latin-1') as f:
            reader = csv.DictReader(f)
            for row in reader:
                nombre = row.get('NOMBRE', '').strip()
                congregacion = row.get('CONGREGACION', '').strip()
                telefono = row.get('TELEFONO', '').strip()

                if nombre and telefono and telefono not in seen_phones:
                    seen_phones.add(telefono)
                    hermanos_data.append({
                        'nombre': nombre,
                        'congregacion': congregacion or "General",
                        'telefono': telefono
                    })

        print(f"📊 Cargando {len(hermanos_data)} hermanos únicos...")

        for i, data in enumerate(hermanos_data, 1):
            hermano_id = str(uuid4())
            cursor.execute("""
                INSERT INTO hermanos (id, nombre, congregacion, telefono, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (telefono) DO NOTHING
            """, (
                hermano_id,
                data['nombre'],
                data['congregacion'],
                data['telefono'],
                True
            ))

            if i % 100 == 0 or i == len(hermanos_data):
                conn.commit()
                print(f"  ✅ {i}/{len(hermanos_data)} hermanos procesados")

        conn.commit()
        print(f"\n✅ {len(hermanos_data)} hermanos cargados exitosamente")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_hermanos()
