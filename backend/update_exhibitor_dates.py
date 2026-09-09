#!/usr/bin/env python3
"""Update exhibitor dates to enable display."""

import os
import psycopg2
from datetime import datetime, timedelta

def update_dates():
    """Update exhibitor open and close dates."""
    user = os.getenv("POSTGRES_USER", "exhibidores")
    password = os.getenv("POSTGRES_PASSWORD", "exhibidores123")
    host = os.getenv("DATABASE_HOST", "ppeam_postgres")
    port = os.getenv("DATABASE_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "exhibidores_db")

    try:
        conn = psycopg2.connect(
            host=host,
            port=int(port),
            database=db,
            user=user,
            password=password
        )
        cursor = conn.cursor()

        print(f"✅ Conectado a {host}:{port}/{db}")

        # Get today and set dates: open today, close 30 days from now
        today = datetime.now().date()
        close_date = today + timedelta(days=30)

        # Update all exhibitors with dates
        cursor.execute("""
            UPDATE exhibitors
            SET open_date = %s, close_date = %s, updated_at = NOW()
            WHERE open_date IS NULL OR close_date IS NULL
        """, (today, close_date))

        updated = cursor.rowcount
        conn.commit()

        print(f"✅ {updated} exhibidores actualizados")
        print(f"   Fechas: {today} → {close_date}")

        # Verify
        cursor.execute("""
            SELECT code, name, open_date, close_date
            FROM exhibitors
            ORDER BY code
        """)

        print("\n📊 Estado actual de exhibidores:")
        for row in cursor.fetchall():
            print(f"   {row[0]:25} {row[1]:35} {row[2]} → {row[3]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_dates()
