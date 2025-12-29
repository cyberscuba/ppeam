#!/usr/bin/env python3
"""Cleanup old rejected requests to free up database space"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models import Request, RequestItem
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(bind=engine)

def cleanup_rejected_requests(days_old=30):
    """Delete rejected requests older than specified days"""
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        logger.info(f"Cleaning rejected requests older than {days_old} days ({cutoff_date})")
        
        # Find rejected requests older than cutoff
        rejected_requests = db.execute(
            select(Request).where(
                Request.status == "rejected",
                Request.updated_at < cutoff_date
            )
        ).scalars().all()
        
        request_ids = [r.id for r in rejected_requests]
        
        if not request_ids:
            logger.info("No rejected requests to clean up")
            return
        
        # Delete request items first (CASCADE should handle this, but being explicit)
        items_deleted = db.execute(
            delete(RequestItem).where(RequestItem.request_id.in_(request_ids))
        ).rowcount
        
        # Delete rejected requests
        requests_deleted = db.execute(
            delete(Request).where(Request.id.in_(request_ids))
        ).rowcount
        
        db.commit()
        
        logger.info(f"✓ Deleted {requests_deleted} rejected requests and {items_deleted} request items")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cleanup old rejected requests")
    parser.add_argument("--days", type=int, default=30, help="Delete requests older than N days (default: 30)")
    args = parser.parse_args()
    
    cleanup_rejected_requests(args.days)

