"""
Create default admin user
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Admin
from passlib.context import CryptContext
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin():
    """Create admin user"""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://exhibidores:exhibidores123@postgres:5432/exhibidores_db")

    engine = create_async_engine(database_url, echo=False, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if admin exists
        from sqlalchemy import select
        result = await session.execute(select(Admin).filter(Admin.username == "admin"))
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print("✅ Admin already exists")
        else:
            # Create admin
            admin = Admin(
                username="admin",
                password_hash=pwd_context.hash("Admin@2026"),
                role="super_admin"
            )
            session.add(admin)
            await session.commit()
            print("✅ Admin user created successfully")
            print("   Username: admin")
            print("   Password: Admin@2026")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
