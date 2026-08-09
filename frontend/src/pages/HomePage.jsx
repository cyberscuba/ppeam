import { useState, useEffect } from 'react'
import { Search, Calendar, MapPin, Clock, User, Users, Wrench } from 'lucide-react'
import client from '../api/client'
import DatePicker from '../components/DatePicker'
import CalendarioMensual from '../components/CalendarioMensual'
import NotificationModal from '../components/NotificationModal'
import logger from '../utils/logger'

// Días de la semana
const WEEKDAYS = {
  0: 'Lunes',
  1: 'Martes',
  2: 'Miércoles',
  3: 'Jueves',
  4: 'Viernes',
  5: 'Sábado',
  6: 'Domingo'
}

// Meses del año
const MONTH_NAMES = [
  '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]

// Función para formatear fecha en español
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr + 'T00:00:00')
  const day = date.getDate()
  const month = MONTH_NAMES[date.getMonth() + 1]
  const year = date.getFullYear()
  return `${day} de ${month} de ${year}`
}

export default function HomePage() {
  const [points, setPoints] = useState([])
  const [phone, setPhone] = useState('')
  const [userFound, setUserFound] = useState(false)
  const [userName, setUserName] = useState('')
  const [genderLabel, setGenderLabel] = useState('Hermano') // Default to 'Hermano'
  const [selectedTurns, setSelectedTurns] = useState([]) // Array of {point_id, schedule_id, date}
  const [loading, setLoading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showDatePicker, setShowDatePicker] = useState(false)
  const [datePickerSchedule, setDatePickerSchedule] = useState(null)
  const [datePickerPointId, setDatePickerPointId] = useState(null)
  const [showClosedModal, setShowClosedModal] = useState(false)
  const [closedExhibitorInfo, setClosedExhibitorInfo] = useState(null)
  const [showCartModal, setShowCartModal] = useState(false)
  const [notification, setNotification] = useState(null) // { type, title, message, details }

  const searchUser = async (e) => {
    e.preventDefault()
    if (!phone) return
    
    setSearching(true)
    try {
      // Buscar hermano por teléfono
      const { data } = await client.get(`/api/api/users/search?phone=${encodeURIComponent(phone)}`)
      if (data.found) {
        setUserFound(true)
        // Usar full_name o nombre según el tipo
        setUserName(data.user.full_name || data.user.nombre || 'Hermano')
        // Usar gender_label del backend si está disponible
        setGenderLabel(data.gender_label || 'Hermano')
        loadPoints()
      } else {
        setNotification({
          type: 'error',
          title: 'Usuario No Encontrado',
          message: 'El teléfono ingresado no está registrado en el sistema.',
          details: ['Por favor, contacte al administrador para registrarse.']
        })
        setPhone('') // Limpiar el campo
      }
    } catch (error) {
      logger.error('Error searching user:', error)
      setNotification({
        type: 'error',
        title: 'Error de Búsqueda',
        message: 'No se pudo buscar el usuario en el sistema.',
        details: [error.response?.data?.detail || error.message]
      })
      setPhone('') // Limpiar el campo en caso de error
    } finally {
      setSearching(false)
    }
  }

  const loadPoints = async () => {
    setLoading(true)
    try {
      // Incluir el teléfono del usuario para filtrar slots ya reservados
      const params = phone ? { phone: phone } : {}
      const { data } = await client.get('/points', { params })
      setPoints(data)
    } catch (error) {
      logger.error('Error loading points:', error)
    } finally {
      setLoading(false)
    }
  }

  const submitRequest = async () => {
    if (!phone || !userFound) {
      setNotification({
        type: 'warning',
        title: 'Autenticación Requerida',
        message: 'Debe buscar y validar su teléfono antes de solicitar turnos.',
        details: []
      })
      return
    }
    
    if (selectedTurns.length === 0) {
      setNotification({
        type: 'warning',
        title: 'Sin Turnos Seleccionados',
        message: 'Debe seleccionar al menos un turno antes de continuar.',
        details: []
      })
      return
    }
    
    setSubmitting(true)
    try {
      const items = selectedTurns.map(turn => ({
        point_id: turn.point_id,
        schedule_id: turn.schedule_id,
        slot_date: turn.date
      }))
      
      const response = await client.post('/api/requests/public', {
        phone: phone,
        items: items
      })
      
      // Check if there were conflicts in the response
      if (response.data.conflicts && response.data.conflicts.length > 0) {
        const conflictMessages = response.data.conflicts.map(c => 
          c.reason || 'Turno no disponible'
        )
        setNotification({
          type: 'warning',
          title: 'Asignación Parcial',
          message: 'Algunos turnos no pudieron ser asignados, pero los disponibles fueron confirmados.',
          details: conflictMessages
        })
        // Reload points to refresh availability
        await loadPoints()
      } else {
        setNotification({
          type: 'success',
          title: '¡Solicitud Exitosa!',
          message: 'Tus turnos han sido confirmados correctamente.',
          details: [
            `${selectedTurns.length} turno${selectedTurns.length !== 1 ? 's' : ''} asignado${selectedTurns.length !== 1 ? 's' : ''}`,
            'Recibirás una notificación con los detalles.'
          ]
        })
        setSelectedTurns([])
        // Reload points to refresh availability after submission (mantener el teléfono para filtrar)
        await loadPoints()
        // NO limpiar el teléfono para que el usuario pueda seguir viendo su disponibilidad
        // setUserFound(false)
        // setPhone('')
        // setGenderLabel('Hermano')
      }
    } catch (error) {
      logger.error('Error en submitRequest:', error)
      logger.error('Error response:', error.response)
      
      if (error.response?.status === 409) {
        // Conflict error - some turns are not available
        const errorDetail = error.response?.data?.detail
        let conflicts = []
        
        // Check if detail is an object with conflicts array
        if (errorDetail && typeof errorDetail === 'object' && errorDetail.conflicts) {
          conflicts = errorDetail.conflicts
        } else if (errorDetail && Array.isArray(errorDetail)) {
          conflicts = errorDetail
        } else if (error.response?.data?.conflicts) {
          conflicts = error.response.data.conflicts
        }
        
        if (conflicts.length > 0) {
          const conflictMessages = conflicts.map(c => 
            c.reason || 'Turno no disponible'
          )
          setNotification({
            type: 'error',
            title: 'Turnos No Disponibles',
            message: 'Los turnos seleccionados ya no están disponibles. Por favor, seleccione otros turnos.',
            details: conflictMessages
          })
        } else {
          setNotification({
            type: 'error',
            title: 'Turnos No Disponibles',
            message: 'Los turnos seleccionados ya no están disponibles. Por favor, seleccione otros turnos.',
            details: []
          })
        }
        // Reload points to refresh availability
        await loadPoints()
      } else {
        const errorMsg = error.response?.data?.detail
        let message = 'Ocurrió un error al procesar su solicitud.'
        let details = []
        
        if (errorMsg && typeof errorMsg === 'object') {
          message = errorMsg.message || message
          if (errorMsg.conflicts) {
            details = errorMsg.conflicts.map(c => c.reason || 'Error desconocido')
          }
        } else if (errorMsg) {
          details = [errorMsg]
        } else {
          details = [error.message]
        }
        
        setNotification({
          type: 'error',
          title: 'Error al Enviar Solicitud',
          message: message,
          details: details
        })
      }
    } finally {
      setSubmitting(false)
    }
  }

  const openDatePicker = (pointId, schedule, point) => {
    // Verificar si el exhibidor está cerrado
    if (point && !point.is_open_for_requests) {
      const openMonth = point.open_date ? MONTH_NAMES[new Date(point.open_date + 'T00:00:00').getMonth() + 1] : 'el próximo mes'
      setClosedExhibitorInfo({
        name: point.name,
        openDate: point.open_date,
        closeDate: point.close_date,
        openMonth: openMonth
      })
      setShowClosedModal(true)
      return
    }
    
    setDatePickerPointId(pointId)
    setDatePickerSchedule(schedule)
    setShowDatePicker(true)
  }

  const handleCalendarSlotSelect = (pointId, dateStr, schedule) => {
    // Check for duplicates
    const isDuplicate = selectedTurns.some(turn => 
      turn.point_id === pointId && 
      turn.schedule_id === schedule.id && 
      turn.date === dateStr
    )
    
    if (isDuplicate) {
      // Don't add duplicate, just return
      return
    }
    
    // Add turn
    setSelectedTurns(prev => [...prev, {
      point_id: pointId,
      schedule_id: schedule.id,
      date: dateStr
    }])
  }

  const handleDateSelect = (selectedDateStr) => {
    if (!datePickerPointId || !datePickerSchedule) return
    
    // Check for duplicates
    const isDuplicate = selectedTurns.some(turn => 
      turn.point_id === datePickerPointId && 
      turn.schedule_id === datePickerSchedule.id && 
      turn.date === selectedDateStr
    )
    
    if (isDuplicate) {
      // Don't show alert, just skip adding duplicate
      return
    }
    
    // Add turn
    setSelectedTurns(prev => [...prev, {
      point_id: datePickerPointId,
      schedule_id: datePickerSchedule.id,
      date: selectedDateStr
    }])
  }

  const handleDatePickerClose = () => {
    setShowDatePicker(false)
    setDatePickerPointId(null)
    setDatePickerSchedule(null)
  }

  const removeTurn = (index) => {
    setSelectedTurns(prev => prev.filter((_, i) => i !== index))
  }

  // Obtener información detallada de un turno seleccionado
  const getTurnDetails = (turn) => {
    const point = points.find(p => p.id === turn.point_id)
    if (!point) return null

    const schedule = point.schedules?.find(s => s.id === turn.schedule_id)
    if (!schedule) return null

    return {
      pointName: point.name,
      date: turn.date,
      time: `${schedule.start_time.slice(0, 5)} - ${schedule.end_time.slice(0, 5)}`,
      weekday: schedule.weekday
    }
  }

  // Función para formatear día de la semana en español
  const formatWeekday = (weekdayNum) => {
    return WEEKDAYS[weekdayNum] || 'N/A'
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* Intro */}
      <div className="mb-8">
        <p className="text-lg" style={{ color: '#0D1214', opacity: 0.8 }}>
          Seleccione los puntos de exhibidor y horarios deseados para su turno
        </p>
      </div>

      {/* Phone Search */}
      {!userFound && (
        <div className="card mb-6" style={{ backgroundColor: 'white' }}>
          <h2 className="text-2xl font-bold mb-4" style={{ color: '#0D1214' }}>
            Buscar por Teléfono
          </h2>
          <p className="mb-4" style={{ color: '#0D1214', opacity: 0.7 }}>
            Ingrese su número de teléfono para ver los puntos de exhibidor disponibles
          </p>
          <form onSubmit={searchUser} className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={24} />
              <input
                type="tel"
                placeholder="3101234567 o +573101234567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="input pl-14 text-lg"
                aria-label="Número de teléfono"
                required
              />
            </div>
            <button
              type="submit"
              disabled={searching}
              className="btn btn-primary"
            >
              {searching ? 'Buscando...' : 'Buscar'}
            </button>
          </form>
        </div>
      )}

      {/* Welcome Message */}
      {userFound && (
        <div className="rounded-lg p-4 mb-6" style={{ backgroundColor: '#6B8B4A', color: '#FCFDFA' }}>
          <p className="font-medium text-lg">
            ¡Bienvenid{genderLabel === 'Hermana' ? 'a' : 'o'}, {userName}!
          </p>
          <p className="opacity-90">
            Seleccione los puntos de exhibidor y horarios que desea solicitar
          </p>
        </div>
      )}

      {/* Points Grid - MOBILE FIRST: 1 columna móvil, 2 tablet, 3 desktop */}
      {userFound && loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
          <p className="mt-4 text-gray-600 text-lg sm:text-xl">Cargando puntos de exhibidor...</p>
        </div>
      ) : userFound ? (
        <>
          {/* Mostrar SOLO exhibidores con fechas de apertura y cierre configuradas */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 md:gap-6 lg:grid-cols-2 lg:gap-8 mb-24 pb-4">
            {points
              .filter(point => point.open_date && point.close_date) // SOLO exhibidores con ambas fechas
              .map((point) => {
              // Verificar si el exhibidor está cerrado por fechas o por turnos completos
              const isClosedByDates = !point.is_open_for_requests
              const allSchedulesFull = point.schedules && point.schedules.every(schedule => {
                if (!schedule.availability) return false
                return Object.values(schedule.availability).every(avail => !avail.available)
              })
              const isClosed = isClosedByDates || allSchedulesFull

              return (
            <div key={point.id} className="bg-white rounded-lg sm:rounded-xl shadow-md overflow-hidden border border-gray-200 hover:border-primary-400 hover:shadow-lg transition-all flex flex-col h-[700px] sm:h-[750px]">
              {/* Header del Card - COMPACTO con altura fija */}
              <div className="bg-gradient-to-r from-primary-600 to-primary-700 p-2 sm:p-3 text-white flex-shrink-0 min-h-[80px] sm:min-h-[90px]">
                <div className="flex items-start gap-1.5 sm:gap-2 mb-2">
                  <MapPin className="flex-shrink-0 mt-0.5" size={16} />
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-sm sm:text-base mb-0.5 break-words leading-tight line-clamp-2">{point.name}</h3>
                    <p className="text-primary-100 text-xs font-medium">{point.code}</p>
                  </div>
                </div>
                
                {point.description && (
                  <p className="mb-2 text-primary-50 text-[11px] sm:text-xs leading-snug line-clamp-1">{point.description}</p>
                )}

                {/* Encargados del Exhibidor en el Header - MÁS COMPACTO */}
                {point.leaders && point.leaders.length > 0 && (
                  <div className="mt-1.5 pt-1.5 border-t border-primary-500">
                    <h4 className="font-medium text-[10px] sm:text-xs text-primary-100 mb-1 flex items-center gap-1">
                      <Users size={12} />
                      <span>Encargados</span>
                    </h4>
                    <div className="space-y-1">
                      {(() => {
                        const positionConfig = {
                          'encargado_turnos_principal': {
                            label: 'Principal',
                            icon: User,
                            color: 'text-blue-200',
                            bgColor: 'bg-blue-900/30',
                            borderColor: 'border-blue-400/50'
                          },
                          'encargado_turnos_remplazo': {
                            label: 'Remplazo',
                            icon: Users,
                            color: 'text-green-200',
                            bgColor: 'bg-green-900/30',
                            borderColor: 'border-green-400/50'
                          },
                          'publicaciones_mantenimiento': {
                            label: 'Publicaciones',
                            icon: Wrench,
                            color: 'text-purple-200',
                            bgColor: 'bg-purple-900/30',
                            borderColor: 'border-purple-400/50'
                          }
                        }

                        const positions = ['encargado_turnos_principal', 'encargado_turnos_remplazo', 'publicaciones_mantenimiento']
                        
                        return positions.map((positionKey) => {
                          const leader = point.leaders.find(l => l.position === positionKey)
                          const config = positionConfig[positionKey]
                          const IconComponent = config.icon
                          
                          if (!leader) return null
                          
                          return (
                            <div 
                              key={positionKey} 
                              className={`flex items-center gap-1 p-1 rounded border ${config.bgColor} ${config.borderColor}`}
                            >
                              <div className={`flex-shrink-0 ${config.color}`}>
                                <IconComponent size={10} strokeWidth={2.5} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className={`font-medium text-[9px] ${config.color} leading-tight`}>
                                  {config.label}
                                </p>
                                <p className="text-white font-semibold text-[11px] truncate">
                                  {leader.admin_name || 'No asignado'}
                                </p>
                              </div>
                            </div>
                          )
                        }).filter(Boolean)
                      })()}
                    </div>
                  </div>
                )}
              </div>

              {/* Contenedor con scroll - Altura flexible */}
              <div className="flex-1 overflow-y-auto exhibitor-card-scroll">
                {/* Foto del Exhibidor - COMPACTA */}
                {point.photo_url && (
                  <img 
                    src={point.photo_url} 
                    alt={point.name}
                    className="w-full h-32 sm:h-40 object-cover flex-shrink-0"
                  />
                )}

                {/* Mensaje de Exhibidor Cerrado o Completo */}
                {isClosed && (
                  <div className="mx-3 sm:mx-4 mt-3 sm:mt-4 mb-2 bg-gradient-to-r from-red-50 to-orange-50 border-2 border-red-300 rounded-xl p-3 sm:p-4">
                    <div className="flex items-start gap-2 sm:gap-3">
                      <div className="flex-shrink-0 text-red-600 mt-0.5">
                        <svg className="h-5 w-5 sm:h-6 sm:w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="font-bold text-red-900 text-sm sm:text-base mb-1">
                          {point.is_exhibitor_full ? '🔴 EXHIBIDOR COMPLETO' : 'Exhibidor Cerrado'}
                        </p>
                        <p className="text-red-800 text-xs sm:text-sm leading-relaxed">
                          {point.is_exhibitor_full 
                            ? 'Todos los turnos están completos.' 
                            : 'Apreciamos mucho tu interés. Actualmente este exhibidor se encuentra cerrado para nuevas solicitudes.'}
                        </p>
                        <p className="text-red-700 text-xs sm:text-sm mt-2 leading-relaxed">
                          Gracias por tu interés en colaborar con la obra, no dejes de visitar este sitio.
                        </p>
                        {point.open_date && (
                          <p className="text-red-700 text-xs sm:text-sm mt-2 font-semibold">
                            📅 Este exhibidor se abrirá el {formatDate(point.open_date)} a las 00:00 horas.
                          </p>
                        )}
                        {point.next_open_date && !point.open_date && (
                          <p className="text-red-700 text-xs mt-2 font-semibold">
                            📅 Próxima apertura: {formatDate(point.next_open_date)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Calendario Mensual con Disponibilidad */}
                <div className="px-3 sm:px-4 py-3 sm:py-4">
                  <CalendarioMensual
                    exhibitor={point}
                    onSelectSlot={(dateStr, schedule) => handleCalendarSlotSelect(point.id, dateStr, schedule)}
                    selectedSlots={selectedTurns}
                    isOpen={point.is_open_for_requests}
                  />
                </div>

                {/* Fin del calendario */}
              </div>
              {/* Fin del contenedor con scroll */}
            </div>
          )
        })}
      </div>
    </>
  ) : null}


      {/* Fixed CTA - MOBILE FIRST */}
      {selectedTurns.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-r from-primary-600 to-primary-700 border-t-2 sm:border-t-4 border-primary-800 p-4 sm:p-6 shadow-2xl z-40">
          <div className="container mx-auto max-w-7xl flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
            <button
              onClick={() => setShowCartModal(true)}
              className="text-white text-center sm:text-left w-full sm:w-auto hover:bg-primary-500/30 rounded-lg p-2 transition-all cursor-pointer"
            >
              <p className="text-lg sm:text-2xl font-bold">
                🛒 {selectedTurns.length} turno{selectedTurns.length !== 1 ? 's' : ''} seleccionado{selectedTurns.length !== 1 ? 's' : ''}
              </p>
              <p className="text-sm sm:text-lg text-primary-100 font-medium">
                {new Set(selectedTurns.map(t => t.point_id)).size} punto{new Set(selectedTurns.map(t => t.point_id)).size !== 1 ? 's' : ''} de exhibidor · Click para ver detalle
              </p>
            </button>
            <button
              onClick={submitRequest}
              disabled={submitting}
              className="bg-white text-primary-700 hover:bg-primary-50 active:scale-95 font-bold text-lg sm:text-xl px-6 sm:px-8 py-3 sm:py-4 rounded-lg sm:rounded-xl shadow-lg transition-all hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto sm:min-w-[250px]"
            >
              {submitting ? 'Enviando...' : '✓ Solicitar Asignación'}
            </button>
          </div>
        </div>
      )}

      {/* Date Picker Modal */}
      {showDatePicker && datePickerSchedule && (
        <DatePicker
          schedule={datePickerSchedule}
          onSelect={handleDateSelect}
          onClose={handleDatePickerClose}
          selectedDates={selectedTurns
            .filter(turn => 
              turn.point_id === datePickerPointId && 
              turn.schedule_id === datePickerSchedule.id
            )
            .map(turn => turn.date)
          }
        />
      )}

      {/* Modal de Exhibidor Cerrado */}
      {showClosedModal && closedExhibitorInfo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6 sm:p-8 animate-fade-in">
            <div className="text-center">
              {/* Ícono de advertencia */}
              <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-orange-100 mb-4">
                <svg className="h-8 w-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>

              {/* Título */}
              <h3 className="text-2xl font-bold text-gray-900 mb-4">
                Asignación Cerrada
              </h3>

              {/* Mensaje */}
              <div className="mb-6 space-y-3">
                <p className="text-lg text-gray-700">
                  La asignación de exhibidores para <strong>{closedExhibitorInfo.openMonth}</strong> está cerrada temporalmente.
                </p>
                
                {closedExhibitorInfo.openDate && (
                  <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4 mt-4">
                    <p className="text-blue-900 font-semibold mb-2">
                      📅 Próxima Apertura
                    </p>
                    <p className="text-blue-800 text-xl font-bold">
                      {formatDate(closedExhibitorInfo.openDate)}
                    </p>
                    {closedExhibitorInfo.closeDate && (
                      <p className="text-blue-700 text-sm mt-2">
                        Cierre: {formatDate(closedExhibitorInfo.closeDate)}
                      </p>
                    )}
                  </div>
                )}

                <p className="text-gray-600 text-sm mt-4">
                  Por favor, regrese en la fecha indicada para realizar su solicitud.
                </p>
              </div>

              {/* Botón cerrar */}
              <button
                onClick={() => setShowClosedModal(false)}
                className="bg-primary-600 hover:bg-primary-700 text-white font-bold py-3 px-8 rounded-xl transition-all text-lg w-full sm:w-auto"
              >
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal del Carrito - Resumen de Turnos */}
      {showCartModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full my-8 animate-fade-in">
            {/* Header del Modal */}
            <div className="bg-gradient-to-r from-primary-600 to-primary-700 text-white p-6 rounded-t-2xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl sm:text-3xl font-bold flex items-center gap-3">
                    🛒 Resumen de Turnos
                  </h2>
                  <p className="text-primary-100 mt-1">
                    {selectedTurns.length} turno{selectedTurns.length !== 1 ? 's' : ''} seleccionado{selectedTurns.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <button
                  onClick={() => setShowCartModal(false)}
                  className="text-white hover:bg-primary-500/30 rounded-full p-2 transition-all"
                  aria-label="Cerrar"
                >
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Lista de Turnos */}
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              {selectedTurns.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p className="text-lg">No hay turnos seleccionados</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {selectedTurns.map((turn, index) => {
                    const details = getTurnDetails(turn)
                    if (!details) return null

                    return (
                      <div 
                        key={index}
                        className="bg-gradient-to-r from-gray-50 to-gray-100 border-2 border-gray-200 rounded-xl p-4 hover:shadow-md transition-all"
                      >
                        <div className="flex items-start justify-between gap-4">
                          {/* Información del turno */}
                          <div className="flex-1 min-w-0">
                            {/* Exhibidor */}
                            <div className="flex items-center gap-2 mb-2">
                              <MapPin className="h-5 w-5 text-primary-600 flex-shrink-0" />
                              <h3 className="text-lg font-bold text-gray-900 truncate">
                                {details.pointName}
                              </h3>
                            </div>

                            {/* Fecha */}
                            <div className="flex items-center gap-2 text-gray-700 mb-1">
                              <Calendar className="h-4 w-4 text-gray-500 flex-shrink-0" />
                              <span className="text-sm font-medium">
                                {formatWeekday(details.weekday)}, {formatDate(details.date)}
                              </span>
                            </div>

                            {/* Horario */}
                            <div className="flex items-center gap-2 text-gray-700">
                              <Clock className="h-4 w-4 text-gray-500 flex-shrink-0" />
                              <span className="text-sm font-medium">
                                {details.time}
                              </span>
                            </div>
                          </div>

                          {/* Botón Eliminar */}
                          <button
                            onClick={() => removeTurn(index)}
                            className="flex-shrink-0 bg-red-500 hover:bg-red-600 text-white p-2 rounded-lg transition-all hover:scale-105 active:scale-95"
                            title="Eliminar turno"
                          >
                            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Footer del Modal */}
            <div className="bg-gray-50 p-6 rounded-b-2xl border-t-2 border-gray-200">
              <div className="flex flex-col sm:flex-row gap-3 justify-between items-center">
                {/* Información de resumen */}
                <div className="text-center sm:text-left">
                  <p className="text-gray-700 font-medium">
                    Total: <span className="font-bold text-primary-700">{selectedTurns.length}</span> turno{selectedTurns.length !== 1 ? 's' : ''}
                  </p>
                  <p className="text-sm text-gray-600">
                    en {new Set(selectedTurns.map(t => t.point_id)).size} exhibidor{new Set(selectedTurns.map(t => t.point_id)).size !== 1 ? 'es' : ''}
                  </p>
                </div>

                {/* Botones de acción */}
                <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
                  <button
                    onClick={() => setShowCartModal(false)}
                    className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-3 px-6 rounded-xl transition-all"
                  >
                    Seguir Eligiendo
                  </button>
                  <button
                    onClick={() => {
                      setShowCartModal(false)
                      submitRequest()
                    }}
                    disabled={submitting || selectedTurns.length === 0}
                    className="bg-primary-600 hover:bg-primary-700 text-white font-bold py-3 px-6 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? 'Enviando...' : '✓ Confirmar Solicitud'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Notificación */}
      {notification && (
        <NotificationModal
          type={notification.type}
          title={notification.title}
          message={notification.message}
          details={notification.details}
          onClose={() => setNotification(null)}
        />
      )}
    </div>
  )
}
