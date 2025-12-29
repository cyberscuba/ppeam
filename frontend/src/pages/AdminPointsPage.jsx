import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, Clock, Edit, Power, ArrowLeft, ToggleLeft, ToggleRight, Plus, Trash } from 'lucide-react'
import client from '../api/client'
import logger from '../utils/logger'
import ConfirmationModal from '../components/ConfirmationModal'
import NotificationModal from '../components/NotificationModal'

// Opciones de días de la semana (disponible para todos los componentes)
const weekdayOptions = [
  { value: null, label: 'Todos los días' },
  { value: 0, label: 'Lunes' },
  { value: 1, label: 'Martes' },
  { value: 2, label: 'Miércoles' },
  { value: 3, label: 'Jueves' },
  { value: 4, label: 'Viernes' },
  { value: 5, label: 'Sábado' },
  { value: 6, label: 'Domingo' }
]

export default function AdminPointsPage() {
  const [points, setPoints] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingPoint, setEditingPoint] = useState(null)
  const [confirmationModal, setConfirmationModal] = useState(null)
  const [notification, setNotification] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadPoints()
  }, [])

  const loadPoints = async () => {
    try {
      // Incluir todos los schedules incluso si el exhibidor está cerrado (para admin)
      const { data } = await client.get('/points?active_only=false&include_all_schedules=true')
      logger.log('Points loaded:', data.length, 'points')
      data.forEach(p => {
        logger.log(`Point ${p.name}:`, {
          id: p.id,
          leadersCount: p.leaders?.length || 0,
          leaders: p.leaders,
          hasLeaders: Array.isArray(p.leaders),
          leadersDetails: p.leaders?.map(l => ({ position: l.position, name: l.admin_name }))
        })
      })
      setPoints(data)
    } catch (error) {
      logger.error('Error loading points:', error)
    } finally {
      setLoading(false)
    }
  }

  const togglePointStatus = async (pointId, currentStatus) => {
    try {
      await client.patch(`/admin/points/${pointId}`, {
        is_active: !currentStatus
      })
      setNotification({
        type: 'success',
        title: 'Estado Actualizado',
        message: 'El estado del punto de exhibidor ha sido actualizado correctamente.',
        details: []
      })
      loadPoints()
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error al Actualizar',
        message: 'No se pudo actualizar el estado del punto de exhibidor.',
        details: [error.response?.data?.detail || error.message]
      })
    }
  }

  const toggleScheduleStatus = async (scheduleId, currentStatus) => {
    try {
      await client.patch(`/admin/schedules/${scheduleId}`, {
        is_active: !currentStatus
      })
      setNotification({
        type: 'success',
        title: 'Estado del Horario Actualizado',
        message: 'El estado de la franja horaria ha sido actualizado correctamente.',
        details: []
      })
      loadPoints()
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error al Actualizar Horario',
        message: 'No se pudo actualizar el estado de la franja horaria.',
        details: [error.response?.data?.detail || error.message]
      })
    }
  }

  const handleSavePoint = async (pointData) => {
    try {
      let savedPoint
      if (editingPoint) {
        const { data } = await client.patch(`/admin/points/${editingPoint.id}`, pointData)
        savedPoint = { ...editingPoint, ...data }
        setEditingPoint(savedPoint)
        loadPoints()
      } else {
        const { data } = await client.post('/admin/points', pointData)
        savedPoint = data
        // Actualizar editingPoint para poder agregar horarios sin cerrar el modal
        setEditingPoint(savedPoint)
        loadPoints()
      }
      return savedPoint
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error',
        message: 'No se pudo guardar el punto de exhibidor.',
        details: [error.response?.data?.detail || error.message]
      })
      throw error
    }
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingPoint(null)
    loadPoints()
  }

  const handleDeletePoint = async (pointId) => {
    setConfirmationModal({
      isOpen: true,
      title: '¿Eliminar Punto de Exhibidor?',
      message: '¿Está seguro de eliminar este punto de exhibidor? Esto eliminará también todas sus franjas horarias.',
      confirmText: 'Sí, Eliminar',
      cancelText: 'Cancelar',
      onConfirm: async () => {
        setConfirmationModal(null)
        try {
          await client.delete(`/admin/points/${pointId}`)
          setNotification({
            type: 'success',
            title: 'Punto Eliminado',
            message: 'El punto de exhibidor ha sido eliminado correctamente.',
            details: []
          })
          loadPoints()
        } catch (error) {
          setNotification({
            type: 'error',
            title: 'Error al Eliminar',
            message: 'No se pudo eliminar el punto de exhibidor.',
            details: [error.response?.data?.detail || error.message]
          })
        }
      },
      onCancel: () => setConfirmationModal(null)
    })
  }

  const handleDeleteSchedule = async (scheduleId) => {
    setConfirmationModal({
      isOpen: true,
      title: '¿Eliminar Franja Horaria?',
      message: '¿Está seguro de eliminar esta franja horaria?',
      confirmText: 'Sí, Eliminar',
      cancelText: 'Cancelar',
      onConfirm: async () => {
        setConfirmationModal(null)
        try {
          await client.delete(`/admin/schedules/${scheduleId}`)
          setNotification({
            type: 'success',
            title: 'Franja Horaria Eliminada',
            message: 'La franja horaria ha sido eliminada correctamente.',
            details: []
          })
          loadPoints()
        } catch (error) {
          setNotification({
            type: 'error',
            title: 'Error al Eliminar',
            message: 'No se pudo eliminar la franja horaria.',
            details: [error.response?.data?.detail || error.message]
          })
        }
      },
      onCancel: () => setConfirmationModal(null)
    })
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <header className="mb-6">
        <button
          onClick={() => navigate('/admin')}
          className="btn btn-secondary mb-4 flex items-center gap-2 text-base py-2.5"
        >
          <ArrowLeft size={20} />
          Volver
        </button>
        <div className="flex flex-col gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
              Gestión de Exhibidores
            </h1>
            <p className="text-gray-600 text-base sm:text-lg">
              Crear, editar y gestionar puntos de exhibidor y sus franjas horarias
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              onClick={() => { setEditingPoint(null); setShowModal(true) }}
              className="btn btn-primary flex items-center justify-center gap-2 py-3 text-base"
            >
              <Plus size={20} />
              Nuevo Exhibidor
            </button>
          </div>
        </div>
      </header>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6">
          {points.map((point) => (
            <div
              key={point.id}
              className={`card flex flex-col ${!point.is_active ? 'opacity-60 bg-gray-100' : ''}`}
            >
              <div className="flex-1">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <MapPin className={point.is_active ? 'text-primary-600' : 'text-gray-400'} size={24} />
                    <div className="min-w-0 flex-1">
                      <h3 className="font-bold text-xl break-words">{point.name}</h3>
                      <p className="text-sm text-gray-600">{point.code}</p>

                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium flex-shrink-0 ${
                    point.is_active 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {point.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </div>

                {point.description && (
                  <p className="text-gray-600 mb-4 break-words">{point.description}</p>
                )}

                {/* Estado de Encargados del Exhibidor */}
                {(() => {
                  logger.log(`Rendering leaders for ${point.name}:`, {
                    hasLeaders: !!point.leaders,
                    isArray: Array.isArray(point.leaders),
                    length: point.leaders?.length,
                    leaders: point.leaders
                  })
                  
                  if (!point.leaders || point.leaders.length === 0) {
                    return null
                  }
                  
                  return (
                    <div className="mb-4 bg-gray-50 rounded-lg p-3">
                      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-3">
                        Estado actual
                      </p>
                      <div className="space-y-2">
                        {(() => {
                          const positionLabels = {
                            'encargado_turnos_principal': 'Encargado Turnos Principal',
                            'encargado_turnos_remplazo': 'Encargado Turnos Remplazo',
                            'publicaciones_mantenimiento': 'Publicaciones y Mantenimiento'
                          }
                          
                          const positions = ['encargado_turnos_principal', 'encargado_turnos_remplazo', 'publicaciones_mantenimiento']
                          
                          return positions.map((positionKey) => {
                            const leader = point.leaders.find(l => l.position === positionKey)
                            
                            logger.log(`Position ${positionKey} for ${point.name}:`, leader)
                            
                            if (!leader) return null
                            
                            return (
                              <div key={positionKey} className="flex items-center text-sm text-gray-700 gap-2">
                                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-green-100 text-green-600 flex-shrink-0">
                                  ✓
                                </span>
                                <div className="flex-1">
                                  <span className="font-semibold">{positionLabels[positionKey]}</span>
                                  <span className="text-gray-600 ml-1">({leader.admin_name || 'N/A'})</span>
                                </div>
                              </div>
                            )
                          }).filter(Boolean)
                        })()}
                      </div>
                    </div>
                  )
                })()}

                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Horarios ({point.schedules.length}):
                  </p>
                  {point.schedules.length === 0 ? (
                    <p className="text-sm text-gray-500 italic py-2 bg-gray-50 rounded p-2">No hay horarios configurados. Edite el exhibidor para agregar horarios.</p>
                  ) : (
                    <div className="border border-gray-300 rounded-lg overflow-hidden">
                      {/* Encabezado de tabla */}
                      <div className="grid grid-cols-12 gap-2 bg-gray-100 border-b border-gray-300 px-3 py-2 font-semibold text-xs text-gray-700">
                        <div className="col-span-4">Día de la Semana</div>
                        <div className="col-span-3 text-center flex items-center justify-center gap-1">
                          <Clock size={14} />
                          <span>Hora Inicio</span>
                        </div>
                        <div className="col-span-3 text-center flex items-center justify-center gap-1">
                          <Clock size={14} />
                          <span>Hora Final</span>
                        </div>
                        <div className="col-span-2 text-center">Estado</div>
                      </div>
                      
                      {/* Filas de horarios */}
                      <div className="max-h-64 overflow-y-auto">
                        {point.schedules.map((schedule, index) => {
                          const weekdayLabel = schedule.weekday !== null && schedule.weekday !== undefined 
                            ? weekdayOptions.find(opt => opt.value === schedule.weekday)?.label || 'Todos los días'
                            : 'Todos los días'
                          
                          // Formatear tiempo correctamente (manejar formato HH:MM:SS o HH:MM)
                          const formatTime = (timeStr) => {
                            if (!timeStr) return ''
                            // Si viene en formato HH:MM:SS, tomar solo HH:MM
                            if (timeStr.length >= 5) {
                              return timeStr.substring(0, 5)
                            }
                            return timeStr
                          }
                          
                          const startTime = formatTime(schedule.start_time)
                          const endTime = formatTime(schedule.end_time)
                          
                          return (
                            <div 
                              key={schedule.id} 
                              className={`grid grid-cols-12 gap-2 px-3 py-2.5 text-sm items-center ${
                                index !== point.schedules.length - 1 ? 'border-b border-gray-200' : ''
                              } ${
                                schedule.is_active 
                                  ? 'bg-white hover:bg-gray-50' 
                                  : 'bg-gray-50 opacity-60'
                              }`}
                            >
                              {/* Día de la semana */}
                              <div className="col-span-4 flex items-center gap-2">
                                <span className="text-base">📅</span>
                                <span className={`font-medium ${schedule.is_active ? 'text-gray-900' : 'text-gray-500'}`}>
                                  {weekdayLabel}
                                </span>
                              </div>
                              
                              {/* Hora inicio */}
                              <div className={`col-span-3 text-center font-semibold ${schedule.is_active ? 'text-gray-900' : 'text-gray-500'}`}>
                                {startTime}
                              </div>
                              
                              {/* Hora final */}
                              <div className={`col-span-3 text-center font-semibold ${schedule.is_active ? 'text-gray-900' : 'text-gray-500'}`}>
                                {endTime}
                              </div>
                              
                              {/* Estado y toggle */}
                              <div className="col-span-2 flex items-center justify-center">
                                <button
                                  onClick={() => toggleScheduleStatus(schedule.id, schedule.is_active)}
                                  className={`p-1.5 rounded-lg transition-colors ${
                                    schedule.is_active
                                      ? 'text-green-600 hover:bg-green-100'
                                      : 'text-gray-400 hover:bg-gray-200'
                                  }`}
                                  title={schedule.is_active ? 'Desactivar horario' : 'Activar horario'}
                                >
                                  {schedule.is_active ? (
                                    <ToggleRight size={22} />
                                  ) : (
                                    <ToggleLeft size={22} />
                                  )}
                                </button>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-2 mt-auto pt-4 border-t border-gray-200">
                <button
                  onClick={() => { setEditingPoint(point); setShowModal(true) }}
                  className="btn btn-primary flex items-center justify-center gap-2 flex-1 py-3 text-base relative"
                  title={point.is_active ? 'Exhibidor activo - Click para editar' : 'Exhibidor inactivo - Click para editar'}
                >
                  <Edit size={20} />
                  Editar
                  <span className={`absolute top-1 right-1 h-2 w-2 rounded-full ${
                    point.is_active ? 'bg-green-500' : 'bg-red-500'
                  }`} title={point.is_active ? 'Activo' : 'Inactivo'} />
                </button>
                <button
                  onClick={() => handleDeletePoint(point.id)}
                  className="btn bg-red-600 text-white hover:bg-red-700 flex items-center justify-center gap-2 flex-1 py-3 text-base"
                >
                  <Trash size={20} />
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal para crear/editar punto */}
      {showModal && (
        <PointModal
          point={editingPoint}
          onClose={handleCloseModal}
          onSave={handleSavePoint}
          onDeleteSchedule={handleDeleteSchedule}
        />
      )}

      {/* Confirmation Modal */}
      {confirmationModal && (
        <ConfirmationModal
          isOpen={confirmationModal.isOpen}
          title={confirmationModal.title}
          message={confirmationModal.message}
          confirmText={confirmationModal.confirmText}
          cancelText={confirmationModal.cancelText}
          onConfirm={confirmationModal.onConfirm}
          onCancel={confirmationModal.onCancel}
        />
      )}

      {/* Notification Modal */}
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

function PointModal({ point: initialPoint, onClose, onSave, onDeleteSchedule }) {
  const [editingPoint, setEditingPoint] = useState(initialPoint)
  const [formData, setFormData] = useState({
    code: initialPoint?.code || '',
    name: initialPoint?.name || '',
    description: initialPoint?.description || '',
    latitude: initialPoint?.latitude || '',
    longitude: initialPoint?.longitude || '',
    max_exhibidores: 1, // Deprecated - usar max_persons_per_slot
    min_persons_per_slot: initialPoint?.min_persons_per_slot || 3,
    max_persons_per_slot: initialPoint?.max_persons_per_slot || 5,
    open_date: initialPoint?.open_date || '',
    close_date: initialPoint?.close_date || '',
    photo_url: initialPoint?.photo_url || '',
    is_active: initialPoint?.is_active ?? true,
    basePointName: initialPoint?.basePointName || '', // Para exhibidores adicionales
    exhibitorNumber: initialPoint?.exhibitorNumber || null // Para exhibidores adicionales
  })
  const [schedules, setSchedules] = useState([])
  const [leaders, setLeaders] = useState([])
  const [admins, setAdmins] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadingSchedules, setLoadingSchedules] = useState(false)
  const [confirmationModal, setConfirmationModal] = useState(null)
  const [notification, setNotification] = useState(null)
  const [newSchedule, setNewSchedule] = useState({
    weekday: null, // null = todos los días, 0-6 = lunes-domingo
    start_time: '',
    end_time: '',
    is_active: true
  })
  
  const [newLeader, setNewLeader] = useState({
    admin_id: '',
    position: 'encargado_turnos_principal'
  })
  
  const positionOptions = [
    { value: 'encargado_turnos_principal', label: 'Encargado Turnos Principal' },
    { value: 'encargado_turnos_remplazo', label: 'Encargado Turnos Remplazo' },
    { value: 'publicaciones_mantenimiento', label: 'Publicaciones y Mantenimiento' }
  ]

  const getWeekdayLabel = (weekday) => {
    if (weekday === null || weekday === undefined) return 'Todos los días'
    const option = weekdayOptions.find(opt => opt.value === weekday)
    return option ? option.label : 'Todos los días'
  }

  // Validar horas: inicio mínimo 6:00 AM, fin máximo 10:00 PM
  const validateTimeRange = (startTime, endTime) => {
    if (!startTime || !endTime) return { valid: false, message: 'Debe completar ambos horarios' }
    
    const [startHour, startMin] = startTime.split(':').map(Number)
    const [endHour, endMin] = endTime.split(':').map(Number)
    
    const startMinutes = startHour * 60 + startMin
    const endMinutes = endHour * 60 + endMin
    
    const minStartMinutes = 6 * 60 // 6:00 AM
    const maxEndMinutes = 22 * 60 // 10:00 PM (22:00)
    
    if (startMinutes < minStartMinutes) {
      return { valid: false, message: 'La hora de inicio debe ser como mínimo 6:00 AM' }
    }
    
    if (endMinutes > maxEndMinutes) {
      return { valid: false, message: 'La hora de fin debe ser como máximo 10:00 PM' }
    }
    
    if (startMinutes >= endMinutes) {
      return { valid: false, message: 'La hora de inicio debe ser anterior a la hora de fin' }
    }
    
    return { valid: true }
  }

  useEffect(() => {
    const currentPoint = initialPoint || editingPoint
    if (currentPoint) {
      // Si es un exhibidor adicional nuevo, preparar el formulario
      if (currentPoint.isAdditional && !currentPoint.id) {
        setFormData({
          code: '',
          name: '',
          description: '',
          latitude: '',
          longitude: '',
          max_exhibidores: 1,
          photo_url: '',
          is_active: true,
          basePointName: '',
          exhibitorNumber: null
        })
      } else {
        setFormData({
          code: currentPoint.code || '',
          name: currentPoint.name || '',
          description: currentPoint.description || '',
          latitude: currentPoint.latitude || '',
          longitude: currentPoint.longitude || '',
          max_exhibidores: 1, // Siempre 1
          photo_url: currentPoint.photo_url || '',
          is_active: currentPoint.is_active ?? true,
          basePointName: currentPoint.basePointName || '',
          exhibitorNumber: currentPoint.exhibitorNumber || null
        })
      }
      if (currentPoint.id) {
        loadPointDetails()
      } else {
        setSchedules([])
      }
    } else {
      setSchedules([])
    }
  }, [initialPoint, editingPoint])

  const loadPointDetails = async () => {
    const currentPoint = initialPoint || editingPoint
    if (!currentPoint || !currentPoint.id) return
    setLoadingSchedules(true)
    try {
      const [pointData, leadersData, adminsData] = await Promise.all([
        client.get(`/admin/points/${currentPoint.id}`),
        client.get(`/admin/exhibitor-leaders?exhibitor_id=${currentPoint.id}`),
        client.get('/admin/admins')
      ])
      setSchedules(pointData.data.schedules || [])
      setLeaders(leadersData.data || [])
      // Filtrar solo admins con rol lider_exhibidor
      setAdmins(adminsData.data.filter(a => a.role === 'lider_exhibidor') || [])
    } catch (error) {
      console.error('Error loading point details:', error)
    } finally {
      setLoadingSchedules(false)
    }
  }
  
  const handleAddLeader = async (adminId, position) => {
    const currentPoint = initialPoint || editingPoint
    if (!currentPoint || !currentPoint.id) return
    
    try {
      const { data } = await client.post('/admin/exhibitor-leaders', {
        admin_id: adminId,
        exhibitor_id: currentPoint.id,
        position: position
      })
      setLeaders([...leaders, data])
      loadPointDetails() // Recargar para obtener nombres
      setNotification({
        type: 'success',
        title: 'Encargado Agregado',
        message: 'El encargado ha sido agregado correctamente.',
        details: []
      })
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error al Agregar Encargado',
        message: 'No se pudo agregar el encargado.',
        details: [error.response?.data?.detail || error.message]
      })
    }
  }
  
  const handleAddLeaderWithPosition = async () => {
    if (!newLeader.admin_id) {
      setNotification({
        type: 'warning',
        title: 'Seleccionar Administrador',
        message: 'Por favor seleccione un administrador.',
        details: []
      })
      return
    }
    
    await handleAddLeader(newLeader.admin_id, newLeader.position)
    
    // Limpiar el formulario
    setNewLeader({
      admin_id: '',
      position: 'encargado_turnos_principal'
    })
  }
  
  const handleUpdateLeader = async (leaderId, updates) => {
    try {
      const { data } = await client.patch(`/admin/exhibitor-leaders/${leaderId}`, updates)
      setLeaders(leaders.map(l => l.id === leaderId ? data : l))
      loadPointDetails() // Recargar para obtener nombres
      setNotification({
        type: 'success',
        title: 'Encargado Actualizado',
        message: 'El encargado ha sido actualizado correctamente.',
        details: []
      })
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error al Actualizar Encargado',
        message: 'No se pudo actualizar el encargado.',
        details: [error.response?.data?.detail || error.message]
      })
    }
  }
  
  const handleDeleteLeader = async (leaderId) => {
    setConfirmationModal({
      isOpen: true,
      title: '¿Eliminar Encargado?',
      message: '¿Está seguro de eliminar este encargado?',
      confirmText: 'Sí, Eliminar',
      cancelText: 'Cancelar',
      onConfirm: async () => {
        setConfirmationModal(null)
        try {
          await client.delete(`/admin/exhibitor-leaders/${leaderId}`)
          setLeaders(leaders.filter(l => l.id !== leaderId))
          setNotification({
            type: 'success',
            title: 'Encargado Eliminado',
            message: 'El encargado ha sido eliminado correctamente.',
            details: []
          })
        } catch (error) {
          setNotification({
            type: 'error',
            title: 'Error al Eliminar Encargado',
            message: 'No se pudo eliminar el encargado.',
            details: [error.response?.data?.detail || error.message]
          })
        }
      },
      onCancel: () => setConfirmationModal(null)
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      // Si es un exhibidor adicional, asegurar que el nombre esté completo
      let pointData = { ...formData }
      if (initialPoint?.isAdditional && !initialPoint?.id) {
        if (!formData.basePointName || !formData.exhibitorNumber) {
          setNotification({
            type: 'warning',
            title: 'Campos Incompletos',
            message: 'Por favor complete el nombre del punto base y el número de exhibidor.',
            details: []
          })
          setLoading(false)
          return
        }
        pointData.name = `${formData.basePointName} Exhibidor ${formData.exhibitorNumber}`
        pointData.max_exhibidores = 1
      }
      const savedPoint = await onSave(pointData)
      // Si es un punto nuevo, actualizar editingPoint para poder agregar horarios
      if (!initialPoint && savedPoint) {
        setEditingPoint(savedPoint)
        // Recargar los detalles del punto guardado
        setTimeout(() => {
          if (savedPoint.id) {
            loadPointDetailsForNewPoint(savedPoint.id)
          }
        }, 500)
      }
    } catch (error) {
      // Error ya manejado en onSave
    } finally {
      setLoading(false)
    }
  }

  const loadPointDetailsForNewPoint = async (pointId) => {
    setLoadingSchedules(true)
    try {
      const { data } = await client.get(`/admin/points/${pointId}`)
      setSchedules(data.schedules || [])
    } catch (error) {
      console.error('Error loading point details:', error)
    } finally {
      setLoadingSchedules(false)
    }
  }

  // Validar que la hora esté en punto (minutos = 00)
  const validateHourOnTheHour = (timeStr) => {
    if (!timeStr) return { valid: true } // Permitir vacío para validación posterior
    const parts = timeStr.split(':')
    if (parts.length < 2) return { valid: false, message: 'Formato de hora inválido' }
    const minutes = parseInt(parts[1], 10)
    if (minutes !== 0) {
      return { 
        valid: false, 
        message: `Solo se permiten horas en punto (00 minutos). La hora ${timeStr} no es válida. Use ${parts[0]}:00` 
      }
    }
    return { valid: true }
  }

  const handleAddSchedule = async () => {
    if (!newSchedule.start_time || !newSchedule.end_time) {
      setNotification({
        type: 'warning',
        title: 'Campos Incompletos',
        message: 'Por favor complete los horarios de inicio y fin.',
        details: []
      })
      return
    }

    // Validar que las horas estén en punto (minutos = 00)
    const startValidation = validateHourOnTheHour(newSchedule.start_time)
    if (!startValidation.valid) {
      setNotification({
        type: 'error',
        title: 'Hora Inválida',
        message: startValidation.message,
        details: []
      })
      return
    }
    const endValidation = validateHourOnTheHour(newSchedule.end_time)
    if (!endValidation.valid) {
      setNotification({
        type: 'error',
        title: 'Hora Inválida',
        message: endValidation.message,
        details: []
      })
      return
    }

    // Validar rango de horas
    const validation = validateTimeRange(newSchedule.start_time, newSchedule.end_time)
    if (!validation.valid) {
      setNotification({
        type: 'error',
        title: 'Rango de Horas Inválido',
        message: validation.message,
        details: []
      })
      return
    }

    const currentPoint = initialPoint || editingPoint
    if (!currentPoint || !currentPoint.id) {
      setNotification({
        type: 'warning',
        title: 'Guardar Primero',
        message: 'Debe guardar el punto primero antes de agregar horarios.',
        details: []
      })
      return
    }

    try {
      // Formatear tiempo a HH:MM:SS
      const startTime = newSchedule.start_time.length === 5 ? newSchedule.start_time + ':00' : newSchedule.start_time
      const endTime = newSchedule.end_time.length === 5 ? newSchedule.end_time + ':00' : newSchedule.end_time
      
      // Convert weekday: if it's null/undefined, send null; otherwise send the number (including 0 for Monday)
      const weekdayValue = (newSchedule.weekday === null || newSchedule.weekday === undefined) ? null : newSchedule.weekday
      
      const { data } = await client.post(`/admin/points/${currentPoint.id}/schedules`, {
        weekday: weekdayValue,
        start_time: startTime,
        end_time: endTime,
        is_active: newSchedule.is_active
      })
      setSchedules([...schedules, data])
      setNewSchedule({ weekday: null, start_time: '', end_time: '', is_active: true })
      setNotification({
        type: 'success',
        title: 'Horario Agregado',
        message: 'La franja horaria ha sido agregada correctamente.',
        details: []
      })
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error al Agregar Horario',
        message: 'No se pudo agregar la franja horaria.',
        details: [error.response?.data?.detail || error.message]
      })
    }
  }

  const handleUpdateSchedule = async (scheduleId, updates) => {
    try {
      // Validar horas si se están actualizando
      if (updates.start_time || updates.end_time) {
        // Obtener los horarios actuales del schedule
        const currentSchedule = schedules.find(s => s.id === scheduleId)
        const startTime = updates.start_time || (currentSchedule?.start_time ? currentSchedule.start_time.substring(0, 5) : '')
        const endTime = updates.end_time || (currentSchedule?.end_time ? currentSchedule.end_time.substring(0, 5) : '')
        
        // Validar que las horas estén en punto (minutos = 00)
        if (updates.start_time) {
          const startValidation = validateHourOnTheHour(startTime)
          if (!startValidation.valid) {
            setNotification({
              type: 'error',
              title: 'Hora Inválida',
              message: startValidation.message,
              details: []
            })
            return
          }
        }
        if (updates.end_time) {
          const endValidation = validateHourOnTheHour(endTime)
          if (!endValidation.valid) {
            setNotification({
              type: 'error',
              title: 'Hora Inválida',
              message: endValidation.message,
              details: []
            })
            return
          }
        }
        
        if (startTime && endTime) {
          const validation = validateTimeRange(startTime, endTime)
          if (!validation.valid) {
            setNotification({
              type: 'error',
              title: 'Rango de Horas Inválido',
              message: validation.message,
              details: []
            })
            return
          }
        }
      }
      
      // Formatear tiempo si viene en formato HH:MM
      const formattedUpdates = { ...updates }
      if (updates.start_time && updates.start_time.length === 5) {
        formattedUpdates.start_time = updates.start_time + ':00'
      }
      if (updates.end_time && updates.end_time.length === 5) {
        formattedUpdates.end_time = updates.end_time + ':00'
      }
      
      // Asegurar que weekday se envíe correctamente (incluyendo 0 para Lunes)
      if ('weekday' in updates) {
        formattedUpdates.weekday = (updates.weekday === null || updates.weekday === undefined) ? null : updates.weekday
      }
      
      const { data } = await client.patch(`/admin/schedules/${scheduleId}`, formattedUpdates)
      setSchedules(schedules.map(s => s.id === scheduleId ? data : s))
      setNotification({
        type: 'success',
        title: 'Horario Actualizado',
        message: 'La franja horaria ha sido actualizada correctamente.',
        details: []
      })
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error al Actualizar Horario',
        message: 'No se pudo actualizar la franja horaria.',
        details: [error.response?.data?.detail || error.message]
      })
    }
  }

  const handleDeleteScheduleLocal = async (scheduleId) => {
    try {
      await onDeleteSchedule(scheduleId)
      setSchedules(schedules.filter(s => s.id !== scheduleId))
    } catch (error) {
      // Error ya manejado en onDeleteSchedule
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-2 sm:p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-xl max-w-4xl w-full p-4 sm:p-6 my-4 sm:my-8 max-h-[95vh] sm:max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6">
              {initialPoint?.isAdditional && !initialPoint?.id 
            ? 'Nuevo Exhibidor Adicional' 
            : (initialPoint || editingPoint) 
              ? 'Editar Exhibidor' 
              : 'Nuevo Exhibidor'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-gray-700 font-medium mb-2">
                Código *
              </label>
              <input
                type="text"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                className="input"
                required
                placeholder="GALE-SR"
              />
            </div>

            <div>
              <label className="block text-gray-700 font-medium mb-2">
                Nombre *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input"
                required
                placeholder="Galería - Sta Rosa"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-700 font-medium mb-2">
              Descripción
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="input"
              rows={3}
              placeholder="Descripción del punto de exhibidor"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-gray-700 font-medium mb-2 text-sm sm:text-base">
                Latitud
              </label>
              <input
                type="number"
                step="any"
                value={formData.latitude}
                onChange={(e) => setFormData({ ...formData, latitude: e.target.value ? parseFloat(e.target.value) : '' })}
                className="input"
                placeholder="4.8133"
              />
            </div>

            <div>
              <label className="block text-gray-700 font-medium mb-2">
                Longitud
              </label>
              <input
                type="number"
                step="any"
                value={formData.longitude}
                onChange={(e) => setFormData({ ...formData, longitude: e.target.value ? parseFloat(e.target.value) : '' })}
                className="input"
                placeholder="-75.6961"
              />
            </div>
          </div>

          {/* Campo para exhibidores adicionales */}
          {initialPoint?.isAdditional && !initialPoint?.id && (
            <div>
              <label className="block text-gray-700 font-medium mb-2">
                Nombre del Exhibidor Base *
              </label>
              <input
                type="text"
                value={formData.basePointName}
                onChange={(e) => {
                  const baseName = e.target.value
                  setFormData({ 
                    ...formData, 
                    basePointName: baseName,
                    name: baseName ? `${baseName} Exhibidor 1` : ''
                  })
                }}
                className="input"
                required
                placeholder="Parque de Cuba"
              />
              <p className="text-sm text-gray-500 mt-1">
                Ingrese el nombre base del punto. El sistema agregará automáticamente "Exhibidor X"
              </p>
            </div>
          )}

          {initialPoint?.isAdditional && !initialPoint?.id && formData.basePointName && (
            <div>
              <label className="block text-gray-700 font-medium mb-2">
                Número de Exhibidor *
              </label>
              <input
                type="number"
                min="1"
                value={formData.exhibitorNumber || 1}
                onChange={(e) => {
                  const num = parseInt(e.target.value) || 1
                  setFormData({ 
                    ...formData, 
                    exhibitorNumber: num,
                    name: formData.basePointName ? `${formData.basePointName} Exhibidor ${num}` : ''
                  })
                }}
                className="input"
                required
              />
              <p className="text-sm text-gray-500 mt-1">
                Número del exhibidor (1, 2, 3, etc.)
              </p>
            </div>
          )}

          <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-3">
            <p className="text-blue-800 text-sm">
              <strong>Nota:</strong> Cada punto permite solo 1 exhibidor por horario. Si necesita más exhibidores, cree puntos adicionales con nombres como "Parque de Cuba Exhibidor 1", "Parque de Cuba Exhibidor 2", etc.
            </p>
          </div>

          <div>
            <label className="block text-gray-700 font-medium mb-2">
              URL de Foto
            </label>
            <input
              type="url"
              value={formData.photo_url}
              onChange={(e) => setFormData({ ...formData, photo_url: e.target.value })}
              className="input"
              placeholder="https://ejemplo.com/foto.jpg"
            />
          </div>

          {/* Capacidad de Personas por Turno */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mínimo Personas por Turno *
              </label>
              <input
                type="number"
                min="1"
                max="9"
                value={formData.min_persons_per_slot}
                onChange={(e) => setFormData({ ...formData, min_persons_per_slot: parseInt(e.target.value) || 3 })}
                className="input"
                placeholder="3"
                required
              />
              <p className="text-xs text-gray-500 mt-1">Mínimo de hermanos por turno (1-9)</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Máximo Personas por Turno *
              </label>
              <input
                type="number"
                min="1"
                max="9"
                value={formData.max_persons_per_slot}
                onChange={(e) => setFormData({ ...formData, max_persons_per_slot: parseInt(e.target.value) || 5 })}
                className="input"
                placeholder="5"
                required
              />
              <p className="text-xs text-gray-500 mt-1">Máximo de hermanos por turno (1-9)</p>
            </div>
          </div>

          {/* Fechas de Apertura y Cierre */}
          <div className="border-t border-gray-200 pt-6 mt-6">
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 mb-4">
              <h4 className="font-bold text-gray-900 mb-2 flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Ventana de Asignación Mensual
              </h4>
              <p className="text-sm text-gray-600">Configure el período en que los hermanos pueden solicitar turnos</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white border-2 border-blue-200 rounded-lg p-4 hover:border-blue-400 transition-colors">
                <label className="block font-semibold text-gray-800 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                  📅 Fecha de Apertura
                </label>
                <input
                  type="date"
                  value={formData.open_date}
                  onChange={(e) => {
                    const openDate = e.target.value
                    if (openDate) {
                      const date = new Date(openDate + 'T00:00:00')
                      date.setMonth(date.getMonth() + 1)
                      const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0)
                      const closeDateStr = lastDay.toISOString().split('T')[0]
                      setFormData(prev => ({ ...prev, open_date: openDate, close_date: closeDateStr }))
                    } else {
                      setFormData(prev => ({ ...prev, open_date: '', close_date: '' }))
                    }
                  }}
                  className="w-full px-4 py-3 text-lg border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                />
                <p className="text-xs text-gray-600 mt-2 italic">Inicio de solicitudes para el próximo mes</p>
              </div>
              
              <div className="bg-gray-50 border-2 border-gray-300 rounded-lg p-4">
                <label className="block font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <svg className="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  🔒 Fecha de Cierre (Automática)
                </label>
                <input
                  type="date"
                  value={formData.close_date}
                  readOnly
                  className="w-full px-4 py-3 text-lg bg-gray-100 border-2 border-gray-300 rounded-lg cursor-not-allowed text-gray-700 font-semibold"
                  title="Se calcula automáticamente como el último día del mes siguiente"
                />
                <p className="text-xs text-gray-600 mt-2 italic flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  Último día del mes siguiente (calculado automáticamente)
                </p>
              </div>
            </div>
          </div>

          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="w-5 h-5"
              />
              <span className="text-gray-700">Exhibidor Activo</span>
            </label>
          </div>

          {/* Gestión de Franjas Horarias */}
          {(!initialPoint && !editingPoint) && (
            <div className="border-t pt-6 mt-6">
              <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
                <p className="text-blue-800 text-sm">
                  💡 <strong>Nota:</strong> Guarde el punto primero para poder agregar franjas horarias.
                </p>
              </div>
            </div>
          )}
          
          {(initialPoint || editingPoint) && (initialPoint?.id || editingPoint?.id) && (
            <div className="border-t pt-6 mt-6">
              <h3 className="text-xl font-bold mb-4">Franjas Horarias</h3>
              
              {/* Lista de horarios existentes */}
              {loadingSchedules ? (
                <div className="text-center py-4">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-primary-600 border-t-transparent"></div>
                </div>
              ) : schedules.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No hay franjas horarias configuradas</p>
              ) : (
                <div className="space-y-2 mb-4">
                  {schedules.map((schedule) => (
                    <div key={schedule.id} className="flex flex-col gap-2 p-3 bg-gray-50 rounded-lg">
                      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                        {/* Día de la semana */}
                        <select
                          value={schedule.weekday === null || schedule.weekday === undefined ? '' : schedule.weekday}
                          onChange={(e) => handleUpdateSchedule(schedule.id, { weekday: e.target.value === '' ? null : parseInt(e.target.value) })}
                          className="input text-base flex-1 sm:flex-none sm:w-40 py-2.5"
                        >
                          {weekdayOptions.map(opt => (
                            <option key={opt.value === null ? 'null' : opt.value} value={opt.value === null ? '' : opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        {/* Horarios - Solo horas en punto (minutos = 00) */}
                        <div className="flex items-center gap-2 flex-1">
                          <input
                            type="time"
                            value={schedule.start_time ? schedule.start_time.substring(0, 5) : ''}
                            onChange={(e) => {
                              let timeValue = e.target.value
                              // Ajustar automáticamente los minutos a 00 si el usuario selecciona minutos diferentes
                              if (timeValue && timeValue.length >= 5) {
                                const [hours, minutes] = timeValue.split(':')
                                if (minutes !== '00') {
                                  timeValue = `${hours}:00`
                                }
                              }
                              handleUpdateSchedule(schedule.id, { start_time: timeValue })
                            }}
                            step="3600"
                            className="input text-base flex-1 py-2.5"
                            title="Solo se permiten horas en punto (ej: 11:00, 16:00)"
                          />
                          <span className="text-gray-600">-</span>
                          <input
                            type="time"
                            value={schedule.end_time ? schedule.end_time.substring(0, 5) : ''}
                            onChange={(e) => {
                              let timeValue = e.target.value
                              // Ajustar automáticamente los minutos a 00 si el usuario selecciona minutos diferentes
                              if (timeValue && timeValue.length >= 5) {
                                const [hours, minutes] = timeValue.split(':')
                                if (minutes !== '00') {
                                  timeValue = `${hours}:00`
                                }
                              }
                              handleUpdateSchedule(schedule.id, { end_time: timeValue })
                            }}
                            step="3600"
                            className="input text-base flex-1 py-2.5"
                            title="Solo se permiten horas en punto (ej: 11:00, 16:00)"
                          />
                        </div>
                        {/* Estado y acciones */}
                        <div className="flex items-center gap-2">
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={schedule.is_active}
                              onChange={(e) => handleUpdateSchedule(schedule.id, { is_active: e.target.checked })}
                              className="w-5 h-5"
                            />
                            <span className="text-sm text-gray-600">Activo</span>
                          </label>
                          <button
                            type="button"
                            onClick={() => handleDeleteScheduleLocal(schedule.id)}
                            className="btn bg-red-600 text-white hover:bg-red-700 p-2.5"
                            title="Eliminar horario"
                          >
                            <Trash size={18} />
                          </button>
                        </div>
                      </div>
                      {/* Mostrar resumen del horario */}
                      <div className="text-xs text-gray-500 pl-1">
                        {getWeekdayLabel(schedule.weekday)} • {schedule.start_time ? schedule.start_time.substring(0, 5) : ''} - {schedule.end_time ? schedule.end_time.substring(0, 5) : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Agregar nuevo horario */}
              <div className="border-t pt-4">
                <h4 className="font-medium mb-3 text-base sm:text-lg">Agregar Nueva Franja Horaria</h4>
                <div className="space-y-3">
                  <div className="flex flex-col sm:flex-row gap-2">
                    {/* Selector de día */}
                    <select
                      value={newSchedule.weekday === null || newSchedule.weekday === undefined ? '' : newSchedule.weekday}
                      onChange={(e) => setNewSchedule({ ...newSchedule, weekday: e.target.value === '' ? null : parseInt(e.target.value) })}
                      className="input flex-1 sm:flex-none sm:w-40 py-2.5 text-base"
                    >
                      {weekdayOptions.map(opt => (
                        <option key={opt.value === null ? 'null' : opt.value} value={opt.value === null ? '' : opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    {/* Horarios - Solo horas en punto (minutos = 00) */}
                    <input
                      type="time"
                      value={newSchedule.start_time}
                      onChange={(e) => {
                        let timeValue = e.target.value
                        // Ajustar automáticamente los minutos a 00 si el usuario selecciona minutos diferentes
                        if (timeValue && timeValue.length >= 5) {
                          const [hours, minutes] = timeValue.split(':')
                          if (minutes !== '00') {
                            timeValue = `${hours}:00`
                          }
                        }
                        setNewSchedule({ ...newSchedule, start_time: timeValue })
                      }}
                      step="3600"
                      className="input flex-1 py-2.5 text-base"
                      placeholder="Hora inicio"
                      title="Solo se permiten horas en punto (ej: 11:00, 16:00)"
                    />
                    <input
                      type="time"
                      value={newSchedule.end_time}
                      onChange={(e) => {
                        let timeValue = e.target.value
                        // Ajustar automáticamente los minutos a 00 si el usuario selecciona minutos diferentes
                        if (timeValue && timeValue.length >= 5) {
                          const [hours, minutes] = timeValue.split(':')
                          if (minutes !== '00') {
                            timeValue = `${hours}:00`
                          }
                        }
                        setNewSchedule({ ...newSchedule, end_time: timeValue })
                      }}
                      step="3600"
                      className="input flex-1 py-2.5 text-base"
                      placeholder="Hora fin"
                      title="Solo se permiten horas en punto (ej: 11:00, 16:00)"
                    />
                    <button
                      type="button"
                      onClick={handleAddSchedule}
                      className="btn btn-primary flex items-center justify-center gap-2 py-2.5 text-base"
                    >
                      <Plus size={20} />
                      Agregar
                    </button>
                  </div>
                  <p className="text-xs text-gray-500">
                    💡 <strong>Ejemplo:</strong> Exhibidor 1 - Lunes y Martes: 8:00-10:00, 10:00-12:00, 12:00-16:00 | Exhibidor 2 - Sábado: 8:00-10:00, 10:00-13:00
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Gestión de Encargados */}
          {(initialPoint || editingPoint) && (initialPoint?.id || editingPoint?.id) && (
            <div className="border-t pt-6 mt-6">
              <h3 className="text-xl font-bold mb-4">Encargados del Exhibidor</h3>
              
              {/* Lista de encargados existentes */}
              {leaders.length === 0 ? (
                <p className="text-gray-500 text-center py-4">No hay encargados asignados</p>
              ) : (
                <div className="space-y-2 mb-4">
                  {leaders.map((leader) => {
                    const positionLabels = {
                      'encargado_turnos_principal': 'Encargado Turnos Principal',
                      'encargado_turnos_remplazo': 'Encargado Turnos Remplazo',
                      'publicaciones_mantenimiento': 'Publicaciones y Mantenimiento',
                      'principal': 'Principal',
                      'suplente': 'Suplente'
                    }
                    return (
                      <div key={leader.id} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-3 bg-gray-50 rounded-lg">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-700">{positionLabels[leader.position] || leader.position}</p>
                          <p className="text-xs text-gray-600">{leader.admin_name || 'N/A'}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <select
                            value={leader.position}
                            onChange={(e) => handleUpdateLeader(leader.id, { position: e.target.value })}
                            className="input text-sm flex-1 sm:flex-none sm:w-48 py-2"
                          >
                            {positionOptions.map(opt => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                          <button
                            type="button"
                            onClick={() => handleDeleteLeader(leader.id)}
                            className="btn bg-red-600 text-white hover:bg-red-700 p-2"
                            title="Eliminar encargado"
                          >
                            <Trash size={16} />
                          </button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Agregar nuevo encargado */}
              <div className="border-t pt-4">
                <h4 className="font-medium mb-3 text-base sm:text-lg">Agregar Nuevo Encargado</h4>
                
                {/* Resumen de encargados actuales */}
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-900 font-medium mb-2">Estado actual:</p>
                  <div className="space-y-1 text-xs text-blue-800">
                    <div className="flex items-center gap-2">
                      <span className={leaders.some(l => l.position === 'encargado_turnos_principal') ? 'text-green-600 font-bold' : 'text-gray-400'}>
                        {leaders.some(l => l.position === 'encargado_turnos_principal') ? '✓' : '○'}
                      </span>
                      <span>Encargado Turnos Principal</span>
                      {leaders.some(l => l.position === 'encargado_turnos_principal') && (
                        <span className="text-green-700 font-medium">
                          ({leaders.find(l => l.position === 'encargado_turnos_principal')?.admin_name})
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={leaders.some(l => l.position === 'encargado_turnos_remplazo') ? 'text-green-600 font-bold' : 'text-gray-400'}>
                        {leaders.some(l => l.position === 'encargado_turnos_remplazo') ? '✓' : '○'}
                      </span>
                      <span>Encargado Turnos Remplazo</span>
                      {leaders.some(l => l.position === 'encargado_turnos_remplazo') && (
                        <span className="text-green-700 font-medium">
                          ({leaders.find(l => l.position === 'encargado_turnos_remplazo')?.admin_name})
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={leaders.some(l => l.position === 'publicaciones_mantenimiento') ? 'text-green-600 font-bold' : 'text-gray-400'}>
                        {leaders.some(l => l.position === 'publicaciones_mantenimiento') ? '✓' : '○'}
                      </span>
                      <span>Publicaciones y Mantenimiento</span>
                      {leaders.some(l => l.position === 'publicaciones_mantenimiento') && (
                        <span className="text-green-700 font-medium">
                          ({leaders.find(l => l.position === 'publicaciones_mantenimiento')?.admin_name})
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex flex-col sm:flex-row gap-2">
                    <select
                      value={newLeader.admin_id}
                      onChange={(e) => setNewLeader({ ...newLeader, admin_id: e.target.value })}
                      className="input flex-1 py-2.5 text-base"
                    >
                      <option value="">Seleccionar administrador...</option>
                      {admins.map(admin => (
                        <option key={admin.id} value={admin.id}>
                          {admin.hermano ? admin.hermano.nombre : admin.user?.full_name} ({admin.username})
                        </option>
                      ))}
                    </select>
                    <select
                      value={newLeader.position}
                      onChange={(e) => setNewLeader({ ...newLeader, position: e.target.value })}
                      className="input flex-1 sm:flex-none sm:w-64 py-2.5 text-base"
                    >
                      {positionOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={handleAddLeaderWithPosition}
                      disabled={!newLeader.admin_id}
                      className="btn btn-primary flex items-center justify-center gap-2 py-2.5 text-base disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Plus size={20} />
                      Agregar
                    </button>
                  </div>
                  <p className="text-xs text-gray-500">
                    💡 <strong>Nota:</strong> Solo se muestran administradores con perfil "Líder de Exhibidor"
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t">
            <button 
              type="submit" 
              disabled={loading}
              className="btn btn-primary flex-1 py-3 text-base"
            >
              {loading ? 'Guardando...' : (initialPoint || editingPoint) ? 'Guardar Cambios' : 'Crear Exhibidor'}
            </button>
            <button 
              type="button" 
              onClick={onClose} 
              className="btn btn-secondary flex-1 py-3 text-base"
            >
              {(!initialPoint && !editingPoint) ? 'Cancelar' : 'Cerrar'}
            </button>
          </div>
        </form>
      </div>

      {/* Confirmation Modal */}
      {confirmationModal && (
        <ConfirmationModal
          isOpen={confirmationModal.isOpen}
          title={confirmationModal.title}
          message={confirmationModal.message}
          confirmText={confirmationModal.confirmText}
          cancelText={confirmationModal.cancelText}
          onConfirm={confirmationModal.onConfirm}
          onCancel={confirmationModal.onCancel}
        />
      )}

      {/* Notification Modal */}
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
