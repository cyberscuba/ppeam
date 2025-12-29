"""
Utilidades para manejo de fechas, franjas quincenales y festivos de Colombia
"""
from datetime import date, timedelta, datetime
from typing import List, Tuple
import calendar

# Festivos fijos de Colombia (día-mes)
FESTIVOS_FIJOS_COLOMBIA = [
    (1, 1),   # Año Nuevo
    (5, 1),   # Día del Trabajo
    (7, 20),  # Día de la Independencia
    (8, 7),   # Batalla de Boyacá
    (12, 8),  # Inmaculada Concepción
    (12, 25), # Navidad
]

# Festivos móviles de Colombia por año (calculados manualmente o con algoritmo)
# Estos se mueven al lunes siguiente si caen en día diferente
FESTIVOS_MOVIBLES_COLOMBIA_2024 = [
    date(2024, 1, 8),   # Epifanía
    date(2024, 3, 25),  # San José
    date(2024, 3, 28),  # Jueves Santo
    date(2024, 3, 29),  # Viernes Santo
    date(2024, 5, 13),  # Ascensión
    date(2024, 6, 3),   # Corpus Christi
    date(2024, 6, 10),  # Sagrado Corazón
    date(2024, 7, 1),   # San Pedro y San Pablo
    date(2024, 8, 19),  # Asunción
    date(2024, 10, 14), # Día de la Raza
    date(2024, 11, 4),  # Todos los Santos
    date(2024, 11, 11), # Independencia de Cartagena
]

FESTIVOS_MOVIBLES_COLOMBIA_2025 = [
    date(2025, 1, 6),   # Epifanía
    date(2025, 3, 24),  # San José
    date(2025, 4, 17),  # Jueves Santo
    date(2025, 4, 18),  # Viernes Santo
    date(2025, 6, 2),   # Ascensión
    date(2025, 6, 23),  # Corpus Christi
    date(2025, 6, 30),  # Sagrado Corazón
    date(2025, 6, 30),  # San Pedro y San Pablo
    date(2025, 8, 18),  # Asunción
    date(2025, 10, 13), # Día de la Raza
    date(2025, 11, 3),  # Todos los Santos
    date(2025, 11, 17), # Independencia de Cartagena
]

# Agregar más años según necesidad
FESTIVOS_POR_YEAR = {
    2024: FESTIVOS_MOVIBLES_COLOMBIA_2024,
    2025: FESTIVOS_MOVIBLES_COLOMBIA_2025,
    # TODO: Agregar 2026-2029
}


def es_festivo_colombia(fecha: date) -> bool:
    """
    Verifica si una fecha es festivo en Colombia
    """
    # Verificar festivos fijos
    if (fecha.day, fecha.month) in FESTIVOS_FIJOS_COLOMBIA:
        return True
    
    # Verificar festivos móviles
    festivos_year = FESTIVOS_POR_YEAR.get(fecha.year, [])
    return fecha in festivos_year


def calcular_dias_en_franja(
    fecha_inicio: date,
    fecha_fin: date,
    weekday: int,
    excluir_festivos: bool = True
) -> List[date]:
    """
    Calcula todas las fechas de un día de la semana específico dentro de una franja.
    
    Args:
        fecha_inicio: Fecha de inicio de la franja
        fecha_fin: Fecha de fin de la franja (inclusive)
        weekday: Día de la semana (0=Lunes, 1=Martes, ..., 6=Domingo)
        excluir_festivos: Si True, excluye festivos de Colombia
    
    Returns:
        Lista de fechas que coinciden con el día de la semana
    
    Ejemplo:
        calcular_dias_en_franja(date(2024, 12, 1), date(2024, 12, 15), 0)
        # Retorna: [date(2024, 12, 2), date(2024, 12, 9), date(2024, 12, 16)]
        # (todos los lunes entre 1-15 diciembre)
    """
    dias = []
    fecha_actual = fecha_inicio
    
    while fecha_actual <= fecha_fin:
        # Verificar si coincide con el día de la semana
        if fecha_actual.weekday() == weekday:
            # Si se excluyen festivos, verificar que no sea festivo
            if excluir_festivos:
                if not es_festivo_colombia(fecha_actual):
                    dias.append(fecha_actual)
            else:
                dias.append(fecha_actual)
        
        fecha_actual += timedelta(days=1)
    
    return dias


def obtener_franja_actual() -> Tuple[date, date]:
    """
    Obtiene la franja quincenal actual (1-15 o 16-fin de mes)
    
    Returns:
        Tupla (fecha_inicio, fecha_fin) de la franja actual
    """
    hoy = date.today()
    
    if hoy.day <= 15:
        # Primera quincena
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy.replace(day=15)
    else:
        # Segunda quincena
        fecha_inicio = hoy.replace(day=16)
        # Último día del mes
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    
    return fecha_inicio, fecha_fin


def obtener_proxima_franja() -> Tuple[date, date]:
    """
    Obtiene la siguiente franja quincenal
    
    Returns:
        Tupla (fecha_inicio, fecha_fin) de la próxima franja
    """
    hoy = date.today()
    
    if hoy.day <= 15:
        # Próxima es segunda quincena del mismo mes
        fecha_inicio = hoy.replace(day=16)
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        fecha_fin = hoy.replace(day=ultimo_dia)
    else:
        # Próxima es primera quincena del siguiente mes
        if hoy.month == 12:
            # Siguiente año
            fecha_inicio = date(hoy.year + 1, 1, 1)
            fecha_fin = date(hoy.year + 1, 1, 15)
        else:
            fecha_inicio = date(hoy.year, hoy.month + 1, 1)
            fecha_fin = date(hoy.year, hoy.month + 1, 15)
    
    return fecha_inicio, fecha_fin


def formatear_hora_en_punto(hora_str: str) -> str:
    """
    Formatea una hora para mostrar solo horas en punto (sin minutos si son :00)
    
    Args:
        hora_str: Hora en formato "HH:MM:SS" o "HH:MM"
    
    Returns:
        Hora formateada: "HH:00" (siempre con :00)
    
    Ejemplo:
        formatear_hora_en_punto("10:00:00") -> "10:00"
        formatear_hora_en_punto("10:30:00") -> "10:30"
    """
    # Extraer solo HH:MM
    if len(hora_str) >= 5:
        return hora_str[:5]
    return hora_str


def generar_horas_en_punto(hora_inicio: int = 6, hora_fin: int = 22, intervalo: int = 2) -> List[Tuple[str, str]]:
    """
    Genera franjas horarias en horas en punto
    
    Args:
        hora_inicio: Hora de inicio (6 = 6:00 AM)
        hora_fin: Hora de fin (22 = 10:00 PM)
        intervalo: Intervalo en horas (2 = franjas de 2 horas)
    
    Returns:
        Lista de tuplas (hora_inicio, hora_fin)
    
    Ejemplo:
        generar_horas_en_punto(8, 14, 2)
        # Retorna: [("08:00", "10:00"), ("10:00", "12:00"), ("12:00", "14:00")]
    """
    franjas = []
    
    for hora in range(hora_inicio, hora_fin, intervalo):
        hora_start = f"{hora:02d}:00"
        hora_end = f"{(hora + intervalo):02d}:00"
        franjas.append((hora_start, hora_end))
    
    return franjas


def calcular_capacidad_total_franja(
    fecha_inicio: date,
    fecha_fin: date,
    weekday: int,
    capacidad_por_dia: int = 2,
    excluir_festivos: bool = True
) -> int:
    """
    Calcula la capacidad total para un horario en una franja
    
    Args:
        fecha_inicio: Inicio de la franja
        fecha_fin: Fin de la franja
        weekday: Día de la semana (0=Lunes, ..., 6=Domingo)
        capacidad_por_dia: Hermanos por día (default: 2)
        excluir_festivos: Si True, excluye festivos
    
    Returns:
        Capacidad total (número de días × capacidad por día)
    
    Ejemplo:
        # 3 lunes en diciembre 1-15, 2 personas por día
        calcular_capacidad_total_franja(date(2024, 12, 1), date(2024, 12, 15), 0, 2)
        # Retorna: 6 (3 días × 2 personas)
    """
    dias = calcular_dias_en_franja(fecha_inicio, fecha_fin, weekday, excluir_festivos)
    return len(dias) * capacidad_por_dia


# Mapeo de nombres de días
DIAS_SEMANA = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo"
}


def obtener_nombre_dia(weekday: int) -> str:
    """Retorna el nombre del día de la semana en español"""
    return DIAS_SEMANA.get(weekday, "Desconocido")

