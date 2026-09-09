#!/usr/bin/env python3
"""Initialize database schema by creating all tables from SQLAlchemy models."""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    """Create all tables in the database."""
    logger.info(f"Initializing database at: {settings.DATABASE_URL}")

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_db())
