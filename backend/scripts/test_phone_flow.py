#!/usr/bin/env python3
"""
Script de pruebas para validar el flujo completo de selección de exhibidor y horarios
con números de teléfono específicos.

Uso:
    python scripts/test_phone_flow.py
"""

import asyncio
import sys
import os
from datetime import date, datetime, timedelta
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func
from app.models import User, Hermano, Exhibitor, Schedule, Slot, RequestItem, Request
from app.config import settings
import json

# Números de teléfono a probar
TEST_PHONES = [
    "3175190777",
    "3116086092",
    "3147330076",
    "3103837115",
    "3147916632",
    "3127582059",
    "3127493870",
    "3117889756",
    "3103818080",
    "3013654385",
    "3053490504",
    "3116217561",
    "3174680784",
    "3126028018",
    "3156829956",
    "3137022158",
    "3132232240"
]

class TestResult:
    def __init__(self, phone):
        self.phone = phone
        self.user_found = False
        self.user_name = None
        self.exhibitors_available = 0
        self.exhibitors_with_slots = 0
        self.total_slots_available = 0
        self.can_select_turns = False
        self.errors = []
        self.warnings = []
        self.success = False

    def to_dict(self):
        return {
            "phone": self.phone,
            "user_found": self.user_found,
            "user_name": self.user_name,
            "exhibitors_available": self.exhibitors_available,
            "exhibitors_with_slots": self.exhibitors_with_slots,
            "total_slots_available": self.total_slots_available,
            "can_select_turns": self.can_select_turns,
            "errors": self.errors,
            "warnings": self.warnings,
            "success": self.success
        }

async def test_phone_flow(phone: str, db: AsyncSession) -> TestResult:
    """Prueba el flujo completo para un número de teléfono"""
    result = TestResult(phone)
    
    try:
        # Paso 1: Buscar usuario por teléfono
        import re
        phone_clean = re.sub(r'\D', '', phone)
        
        # Buscar en tabla Hermano
        hermano_result = await db.execute(
            select(Hermano).where(
                Hermano.is_active == True,
                Hermano.telefono.like(f'%{phone_clean}%')
            )
        )
        hermano = hermano_result.scalar_one_or_none()
        
        # Buscar en tabla User
        user_result = await db.execute(
            select(User).where(
                User.is_active == True,
                User.phone.like(f'%{phone_clean}%')
            )
        )
        user = user_result.scalar_one_or_none()
        
        if not hermano and not user:
            result.errors.append(f"Usuario no encontrado con teléfono {phone}")
            return result
        
        result.user_found = True
        if hermano:
            result.user_name = hermano.nombre
        elif user:
            result.user_name = user.full_name
        
        # Obtener user_id para filtrar slots ya asignados
        user_id = None
        if user:
            user_id = user.id
        elif hermano:
            # Buscar usuario asociado al hermano
            user_by_phone = await db.execute(
                select(User).where(User.phone.like(f'%{phone_clean}%'))
            )
            user_obj = user_by_phone.scalar_one_or_none()
            if user_obj:
                user_id = user_obj.id
        
        # Paso 2: Obtener exhibidores disponibles
        exhibitors_result = await db.execute(
            select(Exhibitor).where(Exhibitor.is_active == True)
        )
        exhibitors = exhibitors_result.scalars().all()
        
        result.exhibitors_available = len(exhibitors)
        
        # Filtrar solo exhibidores con fechas configuradas
        exhibitors_with_dates = [
            e for e in exhibitors 
            if e.open_date and e.close_date
        ]
        
        today = date.today()
        available_exhibitors = []
        
        for exhibitor in exhibitors_with_dates:
            # Verificar si está abierto para solicitudes
            is_open = exhibitor.open_date <= today <= exhibitor.close_date
            
            if not is_open:
                continue
            
            # Obtener schedules activos
            schedules_result = await db.execute(
                select(Schedule).where(
                    Schedule.exhibitor_id == exhibitor.id,
                    Schedule.is_active == True
                )
            )
            schedules = schedules_result.scalars().all()
            
            if not schedules:
                continue
            
            # Calcular rango de fechas (mes del close_date)
            target_year = exhibitor.close_date.year
            target_month = exhibitor.close_date.month
            first_day = date(target_year, target_month, 1)
            last_day = exhibitor.close_date
            
            # Verificar disponibilidad de slots
            slots_count = 0
            for schedule in schedules:
                # Generar fechas del mes
                current_date = first_day
                while current_date <= last_day:
                    # Verificar si el schedule aplica para este día
                    if schedule.weekday is not None:
                        if current_date.weekday() != schedule.weekday:
                            current_date += timedelta(days=1)
                            continue
                    
                    # Buscar slot
                    slot_result = await db.execute(
                        select(Slot).where(
                            Slot.exhibitor_id == exhibitor.id,
                            Slot.schedule_id == schedule.id,
                            Slot.slot_date == current_date
                        )
                    )
                    slot = slot_result.scalar_one_or_none()
                    
                    # Verificar si el usuario ya tiene este slot
                    if user_id and slot:
                        user_slot_result = await db.execute(
                            select(RequestItem).join(Request).where(
                                RequestItem.slot_id == slot.id,
                                Request.user_id == user_id,
                                RequestItem.status == "approved"
                            )
                        )
                        user_has_slot = user_slot_result.scalar_one_or_none() is not None
                        if user_has_slot:
                            current_date += timedelta(days=1)
                            continue
                    
                    # Contar capacidad disponible
                    if slot:
                        approved_count_result = await db.execute(
                            select(func.count(RequestItem.id)).where(
                                RequestItem.slot_id == slot.id,
                                RequestItem.status == "approved"
                            )
                        )
                        approved_count = approved_count_result.scalar() or 0
                        capacity = exhibitor.max_persons_per_slot or 5
                        
                        if approved_count < capacity:
                            slots_count += 1
                    else:
                        # Slot no existe, está disponible
                        slots_count += 1
                    
                    current_date += timedelta(days=1)
            
            if slots_count > 0:
                available_exhibitors.append({
                    "exhibitor": exhibitor,
                    "slots_count": slots_count
                })
                result.total_slots_available += slots_count
        
        result.exhibitors_with_slots = len(available_exhibitors)
        result.can_select_turns = result.total_slots_available > 0
        
        if result.total_slots_available == 0:
            result.warnings.append("No hay slots disponibles para este usuario")
        
        result.success = result.user_found and result.can_select_turns
        
    except Exception as e:
        result.errors.append(f"Error en prueba: {str(e)}")
        import traceback
        result.errors.append(traceback.format_exc())
    
    return result

async def main():
    """Función principal"""
    print("=" * 80)
    print("SCRIPT DE PRUEBAS - FLUJO DE SELECCIÓN DE EXHIBIDOR Y HORARIOS")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Números a probar: {len(TEST_PHONES)}")
    print("=" * 80)
    print()
    
    # Crear conexión a la base de datos
    # Convertir postgresql:// a postgresql+asyncpg:// (igual que database.py)
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True
    )
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    results = []
    
    async with async_session() as db:
        for idx, phone in enumerate(TEST_PHONES, 1):
            print(f"[{idx}/{len(TEST_PHONES)}] Probando teléfono: {phone}")
            result = await test_phone_flow(phone, db)
            results.append(result)
            
            # Mostrar resultado inmediato
            if result.user_found:
                print(f"  ✓ Usuario encontrado: {result.user_name}")
            else:
                print(f"  ✗ Usuario NO encontrado")
            
            if result.exhibitors_with_slots > 0:
                print(f"  ✓ Exhibidores disponibles: {result.exhibitors_with_slots}")
                print(f"  ✓ Slots disponibles: {result.total_slots_available}")
            else:
                print(f"  ⚠ No hay exhibidores con slots disponibles")
            
            if result.errors:
                for error in result.errors:
                    print(f"  ✗ Error: {error}")
            
            if result.warnings:
                for warning in result.warnings:
                    print(f"  ⚠ Advertencia: {warning}")
            
            print()
    
    # Generar reporte
    print("=" * 80)
    print("RESUMEN DE RESULTADOS")
    print("=" * 80)
    
    total_tested = len(results)
    users_found = sum(1 for r in results if r.user_found)
    can_select = sum(1 for r in results if r.can_select_turns)
    total_errors = sum(len(r.errors) for r in results)
    
    print(f"Total probados: {total_tested}")
    print(f"Usuarios encontrados: {users_found} ({users_found/total_tested*100:.1f}%)")
    print(f"Pueden seleccionar turnos: {can_select} ({can_select/total_tested*100:.1f}%)")
    print(f"Total de errores: {total_errors}")
    print()
    
    # Detalles por teléfono
    print("DETALLES POR TELÉFONO:")
    print("-" * 80)
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"{status} {result.phone}: {result.user_name or 'NO ENCONTRADO'}")
        if result.exhibitors_with_slots > 0:
            print(f"    Exhibidores: {result.exhibitors_with_slots}, Slots: {result.total_slots_available}")
        if result.errors:
            for error in result.errors:
                print(f"    ERROR: {error}")
    
    # Guardar reporte en JSON
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tested": total_tested,
            "users_found": users_found,
            "can_select_turns": can_select,
            "total_errors": total_errors
        },
        "results": [r.to_dict() for r in results]
    }
    
    report_file = f"test_phone_flow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"Reporte guardado en: {report_file}")
    print("=" * 80)
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

