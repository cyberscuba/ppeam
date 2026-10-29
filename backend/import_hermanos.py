"""
Import hermanos from CSV file
"""
import asyncio
import csv
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Hermano
from uuid import uuid4


async def import_hermanos(csv_path: str):
    """Import hermanos from CSV"""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://exhibidores:exhibidores123@postgres:5432/exhibidores_db")

    engine = create_async_engine(database_url, echo=False, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    hermanos_list = []
    with open(csv_path, 'r', encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            nombre = row.get('NOMBRE', '').strip()
            congregacion = row.get('CONGREGACION', '').strip()
            telefono = row.get('TELEFONO', '').strip()

            if nombre and telefono:  # Only add if name and phone exist
                hermano = Hermano(
                    id=str(uuid4()),
                    nombre=nombre,
                    congregacion=congregacion or "General",
                    telefono=telefono,
                    is_active=True
                )
                hermanos_list.append(hermano)

    # Remove duplicates by phone
    seen_phones = set()
    unique_hermanos = []
    for h in hermanos_list:
        if h.telefono not in seen_phones:
            seen_phones.add(h.telefono)
            unique_hermanos.append(h)

    # Insert in batches
    async with async_session() as session:
        for i in range(0, len(unique_hermanos), 100):
            batch = unique_hermanos[i:i+100]
            session.add_all(batch)
            try:
                await session.commit()
                print(f"✅ Imported {i+len(batch)}/{len(unique_hermanos)} hermanos")
            except Exception as e:
                print(f"❌ Error importing batch: {e}")
                await session.rollback()

    await engine.dispose()
    print(f"\n✅ Import completed! Total: {len(unique_hermanos)} hermanos (removed {len(hermanos_list) - len(unique_hermanos)} duplicates)")


if __name__ == "__main__":
    csv_file = "/app/ListadoHermanosMetropolitana.csv"
    asyncio.run(import_hermanos(csv_file))
