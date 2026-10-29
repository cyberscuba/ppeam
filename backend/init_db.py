"""
Initialize database - create all tables from models
"""
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.database import Base
from app.config import settings
from app.models import *  # Import all models


async def init_db():
    """Create all tables"""
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        # Create all tables defined in Base.metadata
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
