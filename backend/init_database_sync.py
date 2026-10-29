#!/usr/bin/env python3
"""Initialize database schema synchronously using psycopg2."""

import logging
from sqlalchemy import create_engine
from app.models import Base
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Create all tables in the database synchronously."""
    db_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')
    logger.info(f"Initializing database: {db_url[:50]}...")

    try:
        engine = create_engine(db_url, echo=False)

        with engine.begin() as conn:
            Base.metadata.create_all(conn)

        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        raise
    finally:
        engine.dispose()

if __name__ == "__main__":
    init_db()
