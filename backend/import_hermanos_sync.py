"""
Import hermanos from CSV - Synchronous version
"""
import csv
import os
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

def import_hermanos_sync(csv_path: str):
    """Import hermanos from CSV - Sync version"""
    database_url = os.getenv("DATABASE_URL", "postgresql://exhibidores:exhibidores123@postgres:5432/exhibidores_db")

    # Create sync engine
    engine = create_engine(database_url)

    hermanos_data = []
    seen_phones = set()

    # Read CSV
    with open(csv_path, 'r', encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nombre = row.get('NOMBRE', '').strip()
            congregacion = row.get('CONGREGACION', '').strip()
            telefono = row.get('TELEFONO', '').strip()

            if nombre and telefono and telefono not in seen_phones:
                seen_phones.add(telefono)
                hermanos_data.append({
                    'id': str(uuid4()),
                    'nombre': nombre,
                    'congregacion': congregacion or "General",
                    'telefono': telefono,
                    'genero': 'hermano',
                    'is_active': True
                })

    # Insert using raw SQL to avoid UUID issues
    with engine.begin() as conn:
        for i, hermano in enumerate(hermanos_data):
            sql = text("""
                INSERT INTO hermanos (id, nombre, congregacion, telefono, genero, is_active, created_at)
                VALUES (:id, :nombre, :congregacion, :telefono, :genero, :is_active, NOW())
            """)
            try:
                conn.execute(sql, hermano)
                if (i + 1) % 50 == 0:
                    print(f"✅ Imported {i + 1}/{len(hermanos_data)} hermanos")
            except Exception as e:
                print(f"⚠️  Skipped: {hermano['nombre']} ({hermano['telefono']}) - {str(e)[:50]}")

    print(f"\n✅ Import completed! Total: {len(hermanos_data)} hermanos")
    engine.dispose()


if __name__ == "__main__":
    csv_file = "/app/ListadoHermanosMetropolitana.csv"
    import_hermanos_sync(csv_file)
