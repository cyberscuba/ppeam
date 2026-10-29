#!/usr/bin/env python3
"""Setup default schedules for exhibitors."""

import os
import psycopg2
from uuid import uuid4

def setup_schedules():
    """Create schedules for all exhibitors."""
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

        # Check if schedules already exist
        cursor.execute("SELECT COUNT(*) FROM schedules")
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"✅ Base de datos ya contiene {count} schedules")
            cursor.close()
            conn.close()
            return

        # Get all active exhibitors
        cursor.execute("SELECT id, code, name FROM exhibitors WHERE is_active = true ORDER BY code")
        exhibitors = cursor.fetchall()

        print(f"📊 Creando schedules para {len(exhibitors)} exhibidores...")

        for exhibitor_id, code, name in exhibitors:
            schedules = [
                # Lunes a Viernes: 6:00 AM - 12:00 PM
                {
                    'type': 'weekdays',
                    'weekday': None,
                    'start_time': '06:00:00',
                    'end_time': '12:00:00',
                    'description': 'Lunes a Viernes 6:00 AM - 12:00 PM'
                },
                # Lunes a Viernes: 2:00 PM - 8:00 PM
                {
                    'type': 'weekdays',
                    'weekday': None,
                    'start_time': '14:00:00',
                    'end_time': '20:00:00',
                    'description': 'Lunes a Viernes 2:00 PM - 8:00 PM'
                },
                # Sábados: 8:00 AM - 2:00 PM
                {
                    'type': 'specific_day',
                    'weekday': 5,  # Sábado (0=Lunes, 5=Sábado)
                    'start_time': '08:00:00',
                    'end_time': '14:00:00',
                    'description': 'Sábado 8:00 AM - 2:00 PM'
                },
            ]

            for schedule in schedules:
                schedule_id = str(uuid4())
                cursor.execute("""
                    INSERT INTO schedules
                    (id, exhibitor_id, type, weekday, start_time, end_time, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    schedule_id,
                    exhibitor_id,
                    schedule['type'],
                    schedule['weekday'],
                    schedule['start_time'],
                    schedule['end_time'],
                    True
                ))

            print(f"  ✅ {code}: 3 franjas creadas")

        conn.commit()
        print(f"\n✅ Schedules creados exitosamente")

        # Verify
        cursor.execute("""
            SELECT e.code, COUNT(s.id) as schedule_count
            FROM exhibitors e
            LEFT JOIN schedules s ON e.id = s.exhibitor_id
            GROUP BY e.code
            ORDER BY e.code
        """)

        print("\n📊 Estado de Schedules:")
        for code, schedule_count in cursor.fetchall():
            print(f"   {code}: {schedule_count} franjas")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_schedules()
