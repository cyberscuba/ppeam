#!/usr/bin/env python3
"""
Migration script to add 'type' column to schedules table and backfill data
Safely handles existing schedules without breaking anything

Usage: python migrate_schedules.py
"""

import sqlite3
import sys
from pathlib import Path

def migrate_schedules(db_path: str):
    """Migrate schedules table to add type column with backfill"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Step 1: Check if type column already exists
        cursor.execute("PRAGMA table_info(schedules)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'type' in columns:
            print("✅ Column 'type' already exists. Skipping migration.")
            conn.close()
            return

        print("📋 Starting migration of schedules table...")

        # Step 2: Backup existing schedules
        cursor.execute("SELECT COUNT(*) FROM schedules")
        count = cursor.fetchone()[0]
        print(f"   Backing up {count} existing schedules...")

        # Step 3: Add type column
        print("   Adding 'type' column...")
        cursor.execute("""
            ALTER TABLE schedules
            ADD COLUMN type VARCHAR(20) DEFAULT 'specific_day'
        """)

        # Step 4: Backfill type based on weekday logic
        print("   Backfilling schedule types...")

        # All days: weekday IS NULL
        cursor.execute("""
            UPDATE schedules
            SET type = 'all_days'
            WHERE weekday IS NULL
        """)
        all_days_count = cursor.rowcount
        print(f"      ✓ all_days: {all_days_count}")

        # Weekends: weekday IN (5, 6)
        cursor.execute("""
            UPDATE schedules
            SET type = 'weekends'
            WHERE weekday IN (5, 6)
        """)
        weekends_count = cursor.rowcount
        print(f"      ✓ weekends: {weekends_count}")

        # Specific day: weekday IN (0, 1, 2, 3, 4)
        cursor.execute("""
            UPDATE schedules
            SET type = 'specific_day'
            WHERE weekday IN (0, 1, 2, 3, 4)
        """)
        specific_count = cursor.rowcount
        print(f"      ✓ specific_day: {specific_count}")

        # Step 5: Add index for performance
        print("   Adding index for performance...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_schedules_exhibitor_type_active
            ON schedules(exhibitor_id, type, is_active)
        """)

        # Step 6: Verify migration
        cursor.execute("""
            SELECT type, COUNT(*) as count FROM schedules GROUP BY type
        """)
        results = cursor.fetchall()

        print("\n✅ Migration completed successfully!")
        print("\n   Schedule types breakdown:")
        for type_name, count in results:
            print(f"      • {type_name}: {count}")

        # Final check
        cursor.execute("""
            SELECT COUNT(*) FROM schedules WHERE type IS NULL OR type = ''
        """)
        null_count = cursor.fetchone()[0]

        if null_count > 0:
            print(f"\n⚠️  WARNING: {null_count} schedules have NULL or empty type!")
            return False

        conn.commit()
        print("\n✓ All changes committed to database")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "/opt/exhibidores/backend/data/exhibidores.db"

    # Try local path if running from dev machine
    if not Path(db_path).exists():
        db_path = Path(__file__).parent / "data" / "exhibidores.db"
        if not db_path.exists():
            print(f"❌ Database not found at expected locations")
            sys.exit(1)

    success = migrate_schedules(str(db_path))
    sys.exit(0 if success else 1)
