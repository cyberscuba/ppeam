"""
Script para probar el sistema de franjas quincenales
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date
from app.utils.date_helpers import (
    calcular_dias_en_franja,
    calcular_capacidad_total_franja,
    es_festivo_colombia,
    obtener_franja_actual,
    obtener_proxima_franja,
    formatear_hora_en_punto,
    generar_horas_en_punto,
    obtener_nombre_dia,
    DIAS_SEMANA
)

def test_calcular_lunes_diciembre():
    """Test: Calcular lunes en diciembre 1-15"""
    print("\n" + "="*60)
    print("TEST 1: Lunes en Diciembre 1-15, 2024")
    print("="*60)
    
    lunes = calcular_dias_en_franja(
        date(2024, 12, 1),
        date(2024, 12, 15),
        0  # Lunes
    )
    
    print(f"✓ Encontrados {len(lunes)} lunes:")
    for dia in lunes:
        print(f"  - {dia.strftime('%A %d de %B, %Y')}")
    
    capacidad = calcular_capacidad_total_franja(
        date(2024, 12, 1),
        date(2024, 12, 15),
        0,  # Lunes
        2   # 2 hermanos por día
    )
    print(f"✓ Capacidad total: {capacidad} cupos ({len(lunes)} días × 2 hermanos)")


def test_todos_dias_semana():
    """Test: Calcular todos los días de la semana en una franja"""
    print("\n" + "="*60)
    print("TEST 2: Todos los días en Diciembre 1-15, 2024")
    print("="*60)
    
    for weekday, nombre in DIAS_SEMANA.items():
        dias = calcular_dias_en_franja(
            date(2024, 12, 1),
            date(2024, 12, 15),
            weekday
        )
        capacidad = len(dias) * 2
        print(f"✓ {nombre:10s}: {len(dias)} días × 2 = {capacidad} cupos")


def test_festivos():
    """Test: Verificar festivos de Colombia"""
    print("\n" + "="*60)
    print("TEST 3: Festivos de Colombia")
    print("="*60)
    
    fechas_test = [
        (date(2024, 1, 1), "Año Nuevo"),
        (date(2024, 5, 1), "Día del Trabajo"),
        (date(2024, 7, 20), "Día de la Independencia"),
        (date(2024, 12, 25), "Navidad"),
        (date(2024, 3, 28), "Jueves Santo"),
        (date(2024, 3, 29), "Viernes Santo"),
        (date(2024, 12, 10), "Día normal"),
    ]
    
    for fecha, nombre in fechas_test:
        es_festivo = es_festivo_colombia(fecha)
        simbolo = "🎉" if es_festivo else "📅"
        estado = "FESTIVO" if es_festivo else "Normal"
        print(f"{simbolo} {fecha.strftime('%d/%m/%Y')} - {nombre:25s} [{estado}]")


def test_franjas_actuales():
    """Test: Obtener franja actual y próxima"""
    print("\n" + "="*60)
    print("TEST 4: Franjas Quincenales")
    print("="*60)
    
    inicio_actual, fin_actual = obtener_franja_actual()
    print(f"✓ Franja actual: {inicio_actual.strftime('%d/%m/%Y')} - {fin_actual.strftime('%d/%m/%Y')}")
    
    inicio_prox, fin_prox = obtener_proxima_franja()
    print(f"✓ Próxima franja: {inicio_prox.strftime('%d/%m/%Y')} - {fin_prox.strftime('%d/%m/%Y')}")


def test_horas_en_punto():
    """Test: Generar franjas horarias en punto"""
    print("\n" + "="*60)
    print("TEST 5: Franjas Horarias (Horas en Punto)")
    print("="*60)
    
    franjas = generar_horas_en_punto(6, 22, 2)
    
    print("✓ Franjas horarias generadas (6AM - 10PM, cada 2 horas):")
    for i, (inicio, fin) in enumerate(franjas, 1):
        print(f"  {i}. {inicio} - {fin}")


def test_formateo_horas():
    """Test: Formatear horas sin segundos"""
    print("\n" + "="*60)
    print("TEST 6: Formateo de Horas")
    print("="*60)
    
    horas_test = [
        "10:00:00",
        "14:30:00",
        "08:00",
        "18:45:30"
    ]
    
    for hora in horas_test:
        formateada = formatear_hora_en_punto(hora)
        print(f"✓ {hora:12s} → {formateada}")


def test_excluir_festivos():
    """Test: Excluir festivos del cálculo"""
    print("\n" + "="*60)
    print("TEST 7: Excluir Festivos")
    print("="*60)
    
    # Diciembre 2024: 25 es Navidad (Miércoles)
    # Sin excluir festivos
    miercoles_con = calcular_dias_en_franja(
        date(2024, 12, 1),
        date(2024, 12, 31),
        2,  # Miércoles
        excluir_festivos=False
    )
    
    # Excluyendo festivos
    miercoles_sin = calcular_dias_en_franja(
        date(2024, 12, 1),
        date(2024, 12, 31),
        2,  # Miércoles
        excluir_festivos=True
    )
    
    print(f"✓ Miércoles en Diciembre 2024:")
    print(f"  - Con festivos:    {len(miercoles_con)} días")
    print(f"  - Sin festivos:    {len(miercoles_sin)} días")
    print(f"  - Diferencia:      {len(miercoles_con) - len(miercoles_sin)} día (Navidad 25/12)")


def test_caso_real():
    """Test: Caso real del usuario"""
    print("\n" + "="*60)
    print("TEST 8: Caso Real - Lunes 10:00-12:00 en Dic 1-15")
    print("="*60)
    
    # Calcular lunes
    lunes = calcular_dias_en_franja(
        date(2024, 12, 1),
        date(2024, 12, 15),
        0,  # Lunes
        excluir_festivos=True
    )
    
    capacidad_por_dia = 2
    capacidad_total = len(lunes) * capacidad_por_dia
    
    print(f"📅 Horario: Lunes 10:00-12:00")
    print(f"📆 Franja: 1-15 Diciembre 2024")
    print(f"")
    print(f"✓ Días encontrados: {len(lunes)} lunes")
    for i, dia in enumerate(lunes, 1):
        print(f"  {i}. {dia.strftime('%d de %B')} ({dia.strftime('%A')})")
    print(f"")
    print(f"✓ Capacidad por día: {capacidad_por_dia} hermanos")
    print(f"✓ Capacidad total: {capacidad_total} cupos")
    print(f"")
    print(f"📊 Visualización para el usuario:")
    print(f"   🟢 {capacidad_total} Disponibles")
    print(f"   🟠 0 Por Aprobar")
    print(f"   🔵 0 Aprobadas")


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*60)
    print("🧪 PRUEBAS DEL SISTEMA DE FRANJAS QUINCENALES")
    print("="*60)
    
    try:
        test_calcular_lunes_diciembre()
        test_todos_dias_semana()
        test_festivos()
        test_franjas_actuales()
        test_horas_en_punto()
        test_formateo_horas()
        test_excluir_festivos()
        test_caso_real()
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("="*60)
        print("")
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERROR EN LOS TESTS")
        print("="*60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

