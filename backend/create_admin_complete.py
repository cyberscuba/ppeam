"""
Create admin user with associated system user
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Admin, User
from passlib.context import CryptContext
import os
from uuid import uuid4

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_complete():
    """Create admin user with system user"""
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
            if existing_admin.user_id:
                print(f"   User ID: {existing_admin.user_id}")
            elif existing_admin.hermano_id:
                print(f"   Hermano ID: {existing_admin.hermano_id}")
        else:
            # Create system user for admin
            user_id = str(uuid4())
            system_user = User(
                id=user_id,
                full_name="Sistema Admin",
                phone="+57000000000",
                email="admin@exhibidores.local",
                is_active=True
            )
            session.add(system_user)

            # Create admin linked to system user
            admin = Admin(
                username="admin",
                password_hash=pwd_context.hash("Admin@2026"),
                role="super_admin",
                user_id=user_id
            )
            session.add(admin)
            await session.commit()
            print("✅ Admin user created successfully")
            print("   Username: admin")
            print("   Password: Admin@2026")
            print(f"   System User ID: {user_id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_complete())
