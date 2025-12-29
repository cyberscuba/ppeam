import { useState } from 'react'
import { Calendar, X } from 'lucide-react'

export default function DatePicker({ onSelect, onClose, schedule, selectedDates = [] }) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const [selectedDatesState, setSelectedDatesState] = useState(new Set(selectedDates))
  
  const dates = []
  for (let i = 0; i < 14; i++) {
    const date = new Date(today)
    date.setDate(today.getDate() + i)
    dates.push(date)
  }

  const getAvailabilityForDate = (date) => {
    if (!schedule?.availability) return { available: true, current: 0, capacity: 1, is_past: false, is_too_soon: false }
    const dateStr = date.toISOString().split('T')[0]
    return schedule.availability[dateStr] || { available: true, current: 0, capacity: 1, is_past: false, is_too_soon: false }
  }

  // Filter dates by weekday if schedule has a specific weekday
  const shouldShowDate = (date) => {
    // If weekday is null/undefined, show all dates
    if (schedule?.weekday === null || schedule?.weekday === undefined) {
      return true
    }
    // Python weekday: Monday=0, Sunday=6
    // JavaScript getDay(): Sunday=0, Monday=1, ..., Saturday=6
    // Convert JavaScript day to Python weekday
    const jsDay = date.getDay()
    const pythonWeekday = jsDay === 0 ? 6 : jsDay - 1 // Convert Sunday=0 to Sunday=6, others shift by 1
    return pythonWeekday === schedule.weekday
  }
  
  // Check if date/time is too soon (same day, less than 30 minutes before start)
  const isTimeTooSoon = (date, schedule) => {
    if (!schedule?.start_time) return false
    const today = new Date()
    const checkDate = new Date(date)
    checkDate.setHours(0, 0, 0, 0)
    const todayDate = new Date(today)
    todayDate.setHours(0, 0, 0, 0)
    
    // Only check if it's the same day
    if (checkDate.getTime() !== todayDate.getTime()) return false
    
    // Parse schedule start time
    const [hours, minutes] = schedule.start_time.split(':').map(Number)
    const scheduleStart = new Date(today)
    scheduleStart.setHours(hours, minutes, 0, 0)
    
    // Check if less than 30 minutes until start
    const minutesUntilStart = (scheduleStart - today) / (1000 * 60)
    return minutesUntilStart < 30 && minutesUntilStart > 0
  }

  const handleSelect = (date) => {
    const availability = getAvailabilityForDate(date)
    if (availability.available) {
      const dateStr = date.toISOString().split('T')[0]
      setSelectedDatesState(prev => {
        const newSet = new Set(prev)
        if (newSet.has(dateStr)) {
          newSet.delete(dateStr)
        } else {
          newSet.add(dateStr)
        }
        return newSet
      })
    }
  }

  const handleConfirm = () => {
    if (selectedDatesState.size > 0) {
      // Convert Set to Array to process all dates
      const datesArray = Array.from(selectedDatesState)
      
      // Call onSelect for each selected date
      datesArray.forEach(dateStr => {
        onSelect(dateStr)
      })
      
      // Close modal automatically after confirming (important for elderly users)
      // Close immediately - the state updates will be processed
      onClose()
    }
  }

  const formatDate = (date) => {
    return date.toLocaleDateString('es-CO', { 
      weekday: 'short', 
      day: 'numeric', 
      month: 'short' 
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">Seleccionar Fecha</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={24} />
          </button>
        </div>
        
        <div className="mb-4">
          <p className="text-gray-600 mb-2">
            Horario: <span className="font-semibold">{schedule.start_time} - {schedule.end_time}</span>
          </p>
        </div>

        <div className="mb-2">
          <p className="text-sm text-gray-600">
            Seleccione una o más fechas disponibles. Puede seleccionar múltiples fechas.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-4 max-h-64 overflow-y-auto">
          {dates.filter(date => {
            // Filter by weekday if schedule has a specific weekday
            if (schedule?.weekday !== null && schedule?.weekday !== undefined) {
              return shouldShowDate(date)
            }
            return true
          }).map((date, idx) => {
            const dateStr = date.toISOString().split('T')[0]
            const isSelected = selectedDatesState.has(dateStr)
            const isToday = idx === 0
            const availability = getAvailabilityForDate(date)
            const isFull = !availability.available || availability.current >= availability.capacity
            const isPast = date < today || availability.is_past
            const tooSoon = availability.is_too_soon || isTimeTooSoon(date, schedule)
            const isDisabled = isPast || isFull || tooSoon
            
            return (
              <button
                key={dateStr}
                onClick={() => handleSelect(date)}
                disabled={isDisabled}
                className={`p-3 rounded-lg border-2 text-left transition-colors ${
                  isDisabled
                    ? 'border-gray-200 bg-gray-100 opacity-60 cursor-not-allowed'
                    : isSelected
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-blue-300'
                }`}
                title={
                  isPast ? 'Turno ya pasó' : 
                  tooSoon ? 'Debe seleccionar con al menos 30 minutos de anticipación' : 
                  isFull ? `Completo (${availability.current}/${availability.capacity} hermanos)` : 
                  ''
                }
              >
                <div className="flex items-center gap-2">
                  <Calendar size={16} className={isSelected && !isDisabled ? 'text-blue-600' : isDisabled ? 'text-gray-400' : 'text-gray-400'} />
                  <div className="flex-1">
                    <div className={`font-medium ${isSelected && !isDisabled ? 'text-blue-900' : isDisabled ? 'text-gray-500' : 'text-gray-900'}`}>
                      {formatDate(date)}
                    </div>
                    {isToday && !isDisabled && (
                      <div className="text-xs text-gray-500">Hoy</div>
                    )}
                    {!isPast && !tooSoon && (
                      <div className={`text-xs mt-1 ${isFull ? 'text-red-600 font-semibold' : availability.current > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                        {isFull ? `${availability.current}/${availability.capacity} Lleno` : availability.current > 0 ? `${availability.current}/${availability.capacity}` : 'Disponible'}
                      </div>
                    )}
                    {tooSoon && (
                      <div className="text-xs mt-1 text-orange-600 font-semibold">
                        Muy pronto
                      </div>
                    )}
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {selectedDatesState.size > 0 && (
          <div className="mb-4 p-2 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-900 font-medium">
              {selectedDatesState.size} fecha{selectedDatesState.size !== 1 ? 's' : ''} seleccionada{selectedDatesState.size !== 1 ? 's' : ''}
            </p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleConfirm}
            disabled={selectedDatesState.size === 0}
            className="btn btn-primary flex-1"
          >
            Confirmar ({selectedDatesState.size})
          </button>
          <button
            onClick={onClose}
            className="btn btn-secondary flex-1"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}

