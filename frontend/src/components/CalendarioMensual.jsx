import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight, Calendar, Clock } from 'lucide-react'

const WEEKDAYS_SHORT = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const WEEKDAYS_FULL = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

/**
 * Componente CalendarioMensual
 * Muestra un mes completo con la disponibilidad de turnos por día
 * 
 * @param {Object} props
 * @param {Object} props.exhibitor - Datos del exhibidor con schedules y availability
 * @param {Function} props.onSelectSlot - Callback cuando se selecciona un slot (day, schedule)
 * @param {Array} props.selectedSlots - Array de slots ya seleccionados
 * @param {boolean} props.isOpen - Si el exhibidor está abierto para solicitudes
 */
export default function CalendarioMensual({ exhibitor, onSelectSlot, selectedSlots = [], isOpen = true }) {
  // Calcular el mes objetivo desde las fechas del exhibidor
  const getTargetMonth = () => {
    if (!exhibitor.open_date || !exhibitor.close_date) return new Date()
    
    // El mes objetivo es el del close_date (el mes a mostrar)
    const closeDate = new Date(exhibitor.close_date + 'T00:00:00')
    return new Date(closeDate.getFullYear(), closeDate.getMonth(), 1)
  }
  
  const [currentMonth, setCurrentMonth] = useState(getTargetMonth())
  const [selectedDay, setSelectedDay] = useState(null)
  const [showDayDetails, setShowDayDetails] = useState(false)

  // Obtener el primer y último día del mes actual
  const getMonthBounds = (date) => {
    const year = date.getFullYear()
    const month = date.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    return { firstDay, lastDay }
  }

  // Generar los días del mes con información de disponibilidad
  const generateCalendarDays = () => {
    const { firstDay, lastDay } = getMonthBounds(currentMonth)
    const days = []
    
    // Días vacíos antes del primer día del mes (para alinear con el día de la semana)
    const firstDayOfWeek = (firstDay.getDay() + 6) % 7 // 0=Lunes, 6=Domingo
    for (let i = 0; i < firstDayOfWeek; i++) {
      days.push({ isEmpty: true, key: `empty-start-${i}` })
    }
    
    // Días del mes
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    
    for (let day = 1; day <= lastDay.getDate(); day++) {
      const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day)
      const dateStr = date.toISOString().split('T')[0]
      const isPast = date < today
      
      // Verificar si la fecha está dentro del rango permitido del exhibidor
      let isOutOfRange = false
      if (exhibitor.open_date) {
        const openDate = new Date(exhibitor.open_date + 'T00:00:00')
        if (date < openDate) {
          isOutOfRange = true
        }
      }
      if (exhibitor.close_date) {
        const closeDate = new Date(exhibitor.close_date + 'T00:00:00')
        if (date > closeDate) {
          isOutOfRange = true
        }
      }
      
      // Calcular disponibilidad total para este día
      let totalAvailable = 0
      let totalCapacity = 0
      let hasSchedules = false
      let availableSlots = []
      
      if (exhibitor.schedules) {
        exhibitor.schedules.forEach(schedule => {
          if (!schedule.is_active) return
          
          // Verificar si este horario aplica para este día de la semana
          const dayOfWeek = date.getDay() === 0 ? 6 : date.getDay() - 1 // Convertir domingo=0 a domingo=6
          if (schedule.weekday !== null && schedule.weekday !== dayOfWeek) return
          
          // Verificar disponibilidad en el schedule
          if (schedule.availability && schedule.availability[dateStr]) {
            const avail = schedule.availability[dateStr]
            if (!avail.is_past && !avail.is_too_soon) {
              hasSchedules = true
              // IMPORTANTE: Incluir TODOS los slots (incluso llenos) en el cálculo
              // Esto permite calcular correctamente el porcentaje de disponibilidad
              totalCapacity += avail.capacity || 0
              totalAvailable += avail.available_count || 0  // Será 0 si está lleno
              
              // Solo agregar a availableSlots si realmente está disponible para selección
              if (avail.available) {
                availableSlots.push({
                  schedule: schedule,
                  availability: avail
                })
              }
            }
          }
        })
      }
      
      // Determinar el color según disponibilidad (semáforo)
      let statusColor = 'gray' // Sin horarios
      if (hasSchedules && !isPast && !isOutOfRange) {
        const percentAvailable = totalCapacity > 0 ? (totalAvailable / totalCapacity) * 100 : 0
        
        // Debug: Log para verificar cálculo (remover en producción)
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Calendario] ${dateStr}: ${totalAvailable}/${totalCapacity} = ${percentAvailable.toFixed(1)}%`, {
            totalAvailable,
            totalCapacity,
            percentAvailable,
            hasSchedules
          })
        }
        
        // Lógica de colores: semáforo de disponibilidad
        // Rangos ajustados para mejor visualización
        if (percentAvailable === 0) {
          statusColor = 'red' // Completo (0%)
        } else if (percentAvailable > 0 && percentAvailable <= 33) {
          statusColor = 'orange' // Pocos cupos (1-33%)
        } else if (percentAvailable > 33 && percentAvailable <= 66) {
          statusColor = 'yellow' // Algunos cupos (34-66%)
        } else {
          statusColor = 'green' // Muchos cupos (>66%)
        }
      } else if (isPast || isOutOfRange) {
        statusColor = 'gray'
      }
      
      days.push({
        day,
        date,
        dateStr,
        isPast,
        isOutOfRange,
        hasSchedules,
        totalAvailable,
        totalCapacity,
        statusColor,
        availableSlots,
        isEmpty: false,
        key: `day-${day}`
      })
    }
    
    return days
  }

  const calendarDays = generateCalendarDays()

  // Deshabilitar navegación de meses (solo mostrar el mes configurado)
  const canNavigate = false
  
  const goToPreviousMonth = () => {
    if (!canNavigate) return
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1))
    setSelectedDay(null)
    setShowDayDetails(false)
  }

  const goToNextMonth = () => {
    if (!canNavigate) return
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1))
    setSelectedDay(null)
    setShowDayDetails(false)
  }

  const handleDayClick = (dayData) => {
    if (dayData.isEmpty || dayData.isPast || dayData.isOutOfRange || !dayData.hasSchedules || !isOpen) return
    setSelectedDay(dayData)
    setShowDayDetails(true)
  }

  const handleSlotSelect = (schedule, dayData) => {
    onSelectSlot && onSelectSlot(dayData.dateStr, schedule)
  }

  // Colores para el fondo de la casilla completa
  const getStatusBgClass = (color) => {
    switch (color) {
      case 'green': return 'bg-green-100 border-green-300'
      case 'yellow': return 'bg-yellow-100 border-yellow-300'
      case 'orange': return 'bg-orange-100 border-orange-300'
      case 'red': return 'bg-red-100 border-red-300'
      default: return 'bg-gray-50 border-gray-200'
    }
  }

  const getStatusTextColorClass = (color) => {
    switch (color) {
      case 'green': return 'text-green-800'
      case 'yellow': return 'text-yellow-800'
      case 'orange': return 'text-orange-800'
      case 'red': return 'text-red-800'
      default: return 'text-gray-500'
    }
  }

  const getStatusBorderClass = (color, canSelect) => {
    if (!canSelect) return ''
    switch (color) {
      case 'green': return 'hover:border-green-500 hover:shadow-green-200'
      case 'yellow': return 'hover:border-yellow-500 hover:shadow-yellow-200'
      case 'orange': return 'hover:border-orange-500 hover:shadow-orange-200'
      case 'red': return 'hover:border-red-500 hover:shadow-red-200'
      default: return ''
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Header del calendario */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-4 flex items-center justify-between">
        <button
          onClick={goToPreviousMonth}
          disabled={!canNavigate}
          className={`p-2 rounded-lg transition-colors ${canNavigate ? 'hover:bg-blue-500' : 'opacity-30 cursor-not-allowed'}`}
          aria-label="Mes anterior"
        >
          <ChevronLeft className="h-6 w-6 text-white" />
        </button>
        
        <div className="flex flex-col items-center gap-1 text-white">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            <h3 className="text-xl font-bold">
              {MONTH_NAMES[currentMonth.getMonth()]} {currentMonth.getFullYear()}
            </h3>
          </div>
          <p className="text-xs text-blue-200">
            Agenda mensual
          </p>
        </div>
        
        <button
          onClick={goToNextMonth}
          disabled={!canNavigate}
          className={`p-2 rounded-lg transition-colors ${canNavigate ? 'hover:bg-blue-500' : 'opacity-30 cursor-not-allowed'}`}
          aria-label="Mes siguiente"
        >
          <ChevronRight className="h-6 w-6 text-white" />
        </button>
      </div>

      {/* Días de la semana */}
      <div className="grid grid-cols-7 bg-gray-100 border-b">
        {WEEKDAYS_SHORT.map((day, index) => (
          <div key={index} className="p-2 text-center text-sm font-semibold text-gray-700">
            {day}
          </div>
        ))}
      </div>

      {/* Grid de días */}
      <div className="grid grid-cols-7 gap-0">
        {calendarDays.map((dayData) => {
          if (dayData.isEmpty) {
            return (
              <div
                key={dayData.key}
                className="aspect-square border border-gray-200 bg-gray-50"
              />
            )
          }

          const isSelected = selectedDay?.dateStr === dayData.dateStr
          const canSelect = !dayData.isPast && !dayData.isOutOfRange && dayData.hasSchedules && isOpen

          return (
            <button
              key={dayData.key}
              onClick={() => handleDayClick(dayData)}
              disabled={!canSelect}
              className={`
                aspect-square border-2 p-1 sm:p-2 flex flex-col items-center justify-center
                transition-all relative
                ${canSelect ? 'cursor-pointer hover:shadow-md' : 'cursor-not-allowed'}
                ${isSelected ? 'ring-4 ring-blue-500 ring-offset-2' : ''}
                ${(dayData.isPast || dayData.isOutOfRange) ? 'bg-gray-50 opacity-40 border-gray-200' : ''}
                ${!dayData.isPast && !dayData.isOutOfRange && dayData.hasSchedules ? getStatusBgClass(dayData.statusColor) : ''}
                ${!dayData.isPast && !dayData.isOutOfRange && !dayData.hasSchedules ? 'bg-white border-gray-200' : ''}
                ${getStatusBorderClass(dayData.statusColor, canSelect)}
              `}
            >
              {/* Número del día */}
              <div className={`text-xl sm:text-2xl font-bold mb-1 ${
                (dayData.isPast || dayData.isOutOfRange) 
                  ? 'text-gray-400' 
                  : dayData.hasSchedules 
                    ? getStatusTextColorClass(dayData.statusColor)
                    : 'text-gray-700'
              }`}>
                {dayData.day}
              </div>

              {/* Indicador de disponibilidad - SIN punto, solo texto */}
              {dayData.hasSchedules && !dayData.isPast && !dayData.isOutOfRange && (
                <div className="flex flex-col items-center">
                  {/* Número de cupos disponibles */}
                  <div className={`text-xs sm:text-sm font-bold ${getStatusTextColorClass(dayData.statusColor)}`}>
                    {dayData.totalAvailable}/{dayData.totalCapacity}
                  </div>
                  {/* Porcentaje de disponibilidad */}
                  <div className={`text-[10px] sm:text-xs ${getStatusTextColorClass(dayData.statusColor)} opacity-75`}>
                    {Math.round((dayData.totalAvailable / dayData.totalCapacity) * 100)}%
                  </div>
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Leyenda */}
      <div className="p-3 sm:p-4 bg-gradient-to-r from-gray-50 to-gray-100 border-t-2">
        <div className="text-xs sm:text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
          <span>📊</span>
          <span>Leyenda de Disponibilidad</span>
        </div>
        <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2 sm:gap-4">
          <div className="flex items-center gap-2 bg-white rounded-lg p-2 shadow-sm">
            <div className="w-6 h-6 rounded bg-green-100 border-2 border-green-300 flex items-center justify-center">
              <div className="text-xs font-bold text-green-800">✓</div>
            </div>
            <span className="text-xs sm:text-sm text-gray-700 font-medium">Muchos cupos</span>
          </div>
          <div className="flex items-center gap-2 bg-white rounded-lg p-2 shadow-sm">
            <div className="w-6 h-6 rounded bg-yellow-100 border-2 border-yellow-300 flex items-center justify-center">
              <div className="text-xs font-bold text-yellow-800">~</div>
            </div>
            <span className="text-xs sm:text-sm text-gray-700 font-medium">Algunos</span>
          </div>
          <div className="flex items-center gap-2 bg-white rounded-lg p-2 shadow-sm">
            <div className="w-6 h-6 rounded bg-orange-100 border-2 border-orange-300 flex items-center justify-center">
              <div className="text-xs font-bold text-orange-800">!</div>
            </div>
            <span className="text-xs sm:text-sm text-gray-700 font-medium">Pocos</span>
          </div>
          <div className="flex items-center gap-2 bg-white rounded-lg p-2 shadow-sm">
            <div className="w-6 h-6 rounded bg-red-100 border-2 border-red-300 flex items-center justify-center">
              <div className="text-xs font-bold text-red-800">✕</div>
            </div>
            <span className="text-xs sm:text-sm text-gray-700 font-medium">Completo</span>
          </div>
        </div>
      </div>

      {/* Modal de detalles del día */}
      {showDayDetails && selectedDay && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Header del modal */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-4 sm:p-6 text-white sticky top-0">
              <h3 className="text-xl sm:text-2xl font-bold mb-2">
                {WEEKDAYS_FULL[(selectedDay.date.getDay() + 6) % 7]}
              </h3>
              <p className="text-lg sm:text-xl">
                {selectedDay.day} de {MONTH_NAMES[selectedDay.date.getMonth()]} de {selectedDay.date.getFullYear()}
              </p>
              <p className="text-sm sm:text-base mt-2 opacity-90">
                {selectedDay.totalAvailable} cupos disponibles de {selectedDay.totalCapacity}
              </p>
            </div>

            {/* Lista de horarios disponibles */}
            <div className="p-4 sm:p-6">
              <h4 className="text-lg sm:text-xl font-bold text-gray-800 mb-4">Horarios Disponibles:</h4>
              
              {selectedDay.availableSlots.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p className="text-lg">No hay horarios disponibles para este día</p>
                  <p className="text-sm mt-2">Todos los turnos están completos</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {selectedDay.availableSlots.map((slot, index) => {
                    const { schedule, availability } = slot
                    const current = availability.current || availability.approved_count || 0
                    const capacity = availability.capacity || 5
                    const percentOccupied = capacity > 0 ? (current / capacity) * 100 : 0
                    const percentAvailable = 100 - percentOccupied
                    
                    // Colores según ocupación
                    let bgColor = 'bg-green-50 border-green-300'
                    let textColor = 'text-green-800'
                    let progressColor = 'bg-green-500'
                    
                    if (percentOccupied >= 80) {
                      bgColor = 'bg-red-50 border-red-300'
                      textColor = 'text-red-800'
                      progressColor = 'bg-red-500'
                    } else if (percentOccupied >= 60) {
                      bgColor = 'bg-orange-50 border-orange-300'
                      textColor = 'text-orange-800'
                      progressColor = 'bg-orange-500'
                    } else if (percentOccupied >= 40) {
                      bgColor = 'bg-yellow-50 border-yellow-300'
                      textColor = 'text-yellow-800'
                      progressColor = 'bg-yellow-500'
                    }

                    const isAlreadySelected = selectedSlots.some(
                      s => s.schedule_id === schedule.id && s.date === selectedDay.dateStr
                    )
                    
                    const isConfirmed = availability.is_confirmed || false

                    return (
                      <button
                        key={index}
                        onClick={() => handleSlotSelect(schedule, selectedDay)}
                        disabled={isAlreadySelected}
                        className={`
                          w-full p-4 rounded-lg border-2 transition-all
                          ${bgColor}
                          ${isAlreadySelected ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md cursor-pointer'}
                        `}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <Clock className={`h-6 w-6 ${textColor}`} />
                            <div className="text-left">
                              <div className={`text-xl sm:text-2xl font-bold ${textColor}`}>
                                {schedule.start_time.substring(0, 5)} - {schedule.end_time.substring(0, 5)}
                              </div>
                              {isAlreadySelected && (
                                <div className="text-sm text-gray-600 mt-1">✓ Ya seleccionado</div>
                              )}
                              {isConfirmed && !isAlreadySelected && (
                                <div className="text-xs text-green-600 mt-1 font-semibold">✓ Turno confirmado</div>
                              )}
                            </div>
                          </div>
                          
                          <div className="text-right">
                            <div className={`text-2xl sm:text-3xl font-bold ${textColor}`}>
                              {current}/{capacity}
                            </div>
                            <div className="text-xs sm:text-sm text-gray-600">
                              personas
                            </div>
                          </div>
                        </div>
                        
                        {/* Barra de progreso */}
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div 
                            className={`h-2 rounded-full ${progressColor} transition-all`}
                            style={{ width: `${percentOccupied}%` }}
                          />
                        </div>
                        <div className="text-xs text-gray-500 mt-1 text-right">
                          {Math.round(percentOccupied)}% ocupado
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Footer del modal */}
            <div className="p-4 sm:p-6 bg-gray-50 border-t">
              <button
                onClick={() => setShowDayDetails(false)}
                className="w-full bg-gray-600 hover:bg-gray-700 text-white font-bold py-3 px-6 rounded-lg transition-colors text-lg"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

