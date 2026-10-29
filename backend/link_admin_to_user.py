"""
Link existing admin to a system user
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Admin, User
import os
from uuid import uuid4
from sqlalchemy import select, update

async def link_admin():
    """Link admin to system user"""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://exhibidores:exhibidores123@postgres:5432/exhibidores_db")

    engine = create_async_engine(database_url, echo=False, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get admin
        result = await session.execute(select(Admin).filter(Admin.username == "admin"))
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ Admin not found")
            return

        if admin.user_id:
            print(f"✅ Admin already linked to user {admin.user_id}")
            return

        # Create system user
        user_id = str(uuid4())
        system_user = User(
            id=user_id,
            full_name="Sistema Admin",
            phone="+57000000000",
            email="admin@exhibidores.local",
            is_active=True
        )
        session.add(system_user)
        await session.flush()

        # Update admin with user_id
        admin.user_id = user_id
        await session.commit()
        print("✅ Admin linked to system user successfully")
        print(f"   System User ID: {user_id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(link_admin())
