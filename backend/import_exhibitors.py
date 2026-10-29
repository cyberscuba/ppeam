"""
Import exhibitors from organigrama
"""
import os
from sqlalchemy import create_engine, text
from uuid import uuid4

def import_exhibitors():
    """Import exhibitors from data"""
    database_url = os.getenv("DATABASE_URL", "postgresql://exhibidores:exhibidores123@postgres:5432/exhibidores_db")

    engine = create_engine(database_url)

    # Exhibitors data
    exhibitors_data = [
        {"code": "CUBA", "name": "Punto de Acopio Cuba"},
        {"code": "EL_LAGO", "name": "Punto de Acopio El Lago"},
        {"code": "BOLIVAR_Y_VICTORIA", "name": "Punto de Acopio Bolívar y Victoria"},
        {"code": "EL_PROGRESO", "name": "Punto de Acopio El Progreso"},
        {"code": "MEGACABLE", "name": "Punto de Acopio Megacable"},
        {"code": "LAS_ARAUCARIAS_Y_GALERIA", "name": "Punto de Acopio Las Araucarias y Galería"},
        {"code": "TERMINAL", "name": "Punto de Acopio Terminal"}
    ]

    exhibitors = []
    for data in exhibitors_data:
        exhibitor = {
            'id': str(uuid4()),
            'code': data['code'],
            'name': data['name'],
            'description': f"Punto de acopio {data['name']}",
            'order': len(exhibitors) + 1,
            'is_active': True
        }
        exhibitors.append(exhibitor)

    # Insert using raw SQL
    with engine.begin() as conn:
        for exhibitor in exhibitors:
            sql = text("""
                INSERT INTO exhibitors (id, code, name, description, "order", is_active, created_at)
                VALUES (:id, :code, :name, :description, :order, :is_active, NOW())
                ON CONFLICT (code) DO NOTHING
            """)
            conn.execute(sql, exhibitor)
            print(f"✅ Cargado: {exhibitor['name']}")

    print(f"\n✅ {len(exhibitors)} exhibidores importados")
    engine.dispose()


if __name__ == "__main__":
    import_exhibitors()
