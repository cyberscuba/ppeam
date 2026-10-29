// BUILD TIMESTAMP: 2026-09-09-18-30 - VERIFY THIS APPEARS
import { useState, useEffect } from 'react'
import logger from '../utils/logger'
import { useNavigate } from 'react-router-dom'
import { 
  CheckCircle, XCircle, Clock, Search, Calendar, Users, 
  BarChart3, AlertCircle, Filter, Unlock, MapPin
} from 'lucide-react'
import client from '../api/client'
import { useAuthStore } from '../store/authStore'
import NotificationModal from '../components/NotificationModal'
import ConfirmationModal from '../components/ConfirmationModal'

export default function AdminPage() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('approved')
  const [availabilitySummary, setAvailabilitySummary] = useState({
    available: 0,
    occupied: 0,
    total: 0
  })

  // Nuevas estadísticas
  const [monthlyStats, setMonthlyStats] = useState([])
  const [hermanoStats, setHermanoStats] = useState([])
  const [hermanoPage, setHermanoPage] = useState(1)
  const [hermanoPagination, setHermanoPagination] = useState({ page: 1, limit: 50, total: 0, total_pages: 1 })
  const [requestCounts, setRequestCounts] = useState({ approved: 0, cancelled: 0 })

  // Filtros adicionales
  const [searchTerm, setSearchTerm] = useState('')
  const [exhibitorFilter, setExhibitorFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [exhibitors, setExhibitors] = useState([])

  const [notification, setNotification] = useState(null)
  const [confirmationModal, setConfirmationModal] = useState(null)
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/api/admin/login')
      return
    }
    loadRequests()
    loadAvailabilitySummary()
    loadExhibitors()
    loadMonthlyStats()
    loadHermanoStats(1)
  }, [filter, isAuthenticated, navigate])

  useEffect(() => {
    if (hermanoPage !== 1) {
      loadHermanoStats(hermanoPage)
    }
  }, [hermanoPage])

  const loadExhibitors = async () => {
    try {
      const { data } = await client.get('/api/points?active_only=false')
      if (!Array.isArray(data)) {
        logger.error('Error: exhibitors response is not an array', data)
        setExhibitors([])
        return
      }
      setExhibitors(data)
    } catch (error) {
      logger.error('Error loading exhibitors:', error)
      setExhibitors([])
    }
  }

  const loadRequests = async () => {
    try {
      const { data } = await client.get(`/api/admin/requests?status=${filter}`)
      if (!Array.isArray(data)) {
        logger.error('Error: requests response is not an array', data)
        setRequests([])
        return
      }
      setRequests(data)

      // Actualizar contador de estados
      const approvedCount = data.length
      setRequestCounts(prev => ({
        ...prev,
        [filter]: approvedCount
      }))
    } catch (error) {
      logger.error('Error loading requests:', error)
      setRequests([])
      if (error.response?.status === 403 || error.response?.status === 401) {
        setNotification({
          type: 'error',
          title: 'Acceso Denegado',
          message: 'Se requieren permisos de administrador.',
          details: []
        })
        useAuthStore.getState().logout()
        navigate('/api/admin/login')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadMonthlyStats = async () => {
    try {
      const { data } = await client.get('/api/admin/dashboard/stats-by-month')
      setMonthlyStats(data || [])
    } catch (error) {
      logger.error('Error loading monthly stats:', error)
      setMonthlyStats([])
    }
  }

  const loadHermanoStats = async (page = 1) => {
    try {
      const { data } = await client.get(`/api/admin/dashboard/hermanos-by-turns?page=${page}&limit=50`)
      setHermanoStats(data.data || [])
      setHermanoPagination(data.pagination || { page: 1, limit: 50, total: 0, total_pages: 1 })
    } catch (error) {
      logger.error('Error loading hermano stats:', error)
      setHermanoStats([])
    }
  }

  const loadAvailabilitySummary = async () => {
    try {
      const { data: points } = await client.get('/api/points')

      if (!Array.isArray(points)) {
        logger.error('Error: availability summary response is not an array', points)
        setAvailabilitySummary({ available: 0, occupied: 0, total: 0, available_hours: 0, occupied_hours: 0, total_hours: 0 })
        return
      }

      let available = 0
      let occupied = 0
      let available_hours = 0
      let occupied_hours = 0

      points.forEach(point => {
        point.schedules?.forEach(schedule => {
          if (schedule.availability) {
            Object.values(schedule.availability).forEach(avail => {
              // Calcular horas basadas en el horario
              const hoursDiff = 1 // Asumimos slots de 1 hora por defecto
              
              if (avail.available && avail.available_count > 0) {
                available += avail.available_count
                available_hours += avail.available_count * hoursDiff
              }
              
              if (avail.approved_count > 0) {
                occupied += avail.approved_count
                occupied_hours += avail.approved_count * hoursDiff
              }
            })
          }
        })
      })
      
      setAvailabilitySummary({
        available,
        occupied,
        total: available + occupied,
        available_hours,
        occupied_hours,
        total_hours: available_hours + occupied_hours
      })
    } catch (error) {
      logger.error('Error loading availability summary:', error)
    }
  }

  const handleLiberarTurno = async (requestId, itemId) => {
    // Mostrar modal de confirmación en lugar de confirm() nativo
    setConfirmationModal({
      isOpen: true,
      title: '¿Liberar Turno?',
      message: '¿Está seguro de que desea liberar este turno? El espacio quedará disponible y se enviará una notificación a todos los hermanos informando que hay un turno libre.',
      confirmText: 'Sí, Liberar',
      cancelText: 'Cancelar',
      onConfirm: async () => {
        setConfirmationModal(null)
        try {
          await client.post(`/api/admin/requests/${requestId}/approve`, { 
            action: 'reject', // Backend mantiene 'reject' pero frontend muestra 'liberar'
            item_ids: [itemId]
          })
          
          setNotification({
            type: 'success',
            title: 'Turno Liberado',
            message: 'El turno ha sido liberado exitosamente. Se está enviando una notificación a todos los hermanos informando que hay un turno disponible.',
            details: [
              'Los hermanos recibirán un SMS con la fecha, hora y exhibidor del turno liberado.',
              'El turno quedará disponible para que cualquier hermano lo reserve.'
            ]
          })
          
          loadRequests()
          loadAvailabilitySummary()
        } catch (error) {
          setNotification({
            type: 'error',
            title: 'Error al Liberar',
            message: 'No se pudo liberar el turno.',
            details: [error.response?.data?.detail || error.message]
          })
        }
      },
      onCancel: () => {
        setConfirmationModal(null)
      }
    })
  }

  // Aplanar items para mostrar en tabla
  const getTableRows = () => {
    const rows = []
    requests.forEach(request => {
      request.items?.forEach(item => {
        rows.push({
          id: item.id,
          request_id: request.id,
          point_name: item.point?.name || 'N/A',
          point_code: item.point?.code || '',
          exhibitor_id: item.point?.id || '',
          schedule: item.schedule ? `${item.schedule.start_time.substring(0, 5)} - ${item.schedule.end_time.substring(0, 5)}` : 'N/A',
          date: item.date ? new Date(item.date + 'T00:00:00').toLocaleDateString('es-CO', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          }) : 'N/A',
          dateRaw: item.date || '',
          applicant_name: request.user?.full_name || 'N/A',
          applicant_phone: request.user?.phone || 'N/A',
          status: item.status,
          request_status: request.status,
          approver_name: item.approver_name || null,
          created_at: request.created_at
        })
      })
    })
    return rows
  }

  // Aplicar filtros de búsqueda
  const getFilteredRows = () => {
    let rows = getTableRows()
    
    // Filtro de texto (nombre o teléfono)
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      rows = rows.filter(row => 
        row.applicant_name.toLowerCase().includes(search) ||
        row.applicant_phone.toLowerCase().includes(search)
      )
    }
    
    // Filtro de exhibidor
    if (exhibitorFilter) {
      rows = rows.filter(row => row.exhibitor_id === exhibitorFilter)
    }
    
    // Filtro de fecha
    if (dateFilter) {
      rows = rows.filter(row => row.dateRaw === dateFilter)
    }
    
    return rows
  }

  const handleLogout = () => {
    useAuthStore.getState().logout()
    navigate('/api/admin/login')
  }

  const filteredRows = getFilteredRows()

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* Header */}
      <header className="mb-8">
        <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-6 text-white shadow-lg mb-6">
          <h1 className="text-3xl sm:text-4xl font-bold mb-2 flex items-center gap-3">
            <BarChart3 className="h-10 w-10" />
            Panel de Administración
          </h1>
          <p className="text-primary-100 text-lg">
            Gestión profesional de turnos y exhibidores
          </p>
        </div>
        
        {/* Navigation Buttons */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <button
            onClick={() => navigate('/api/admin/users')}
            className="btn btn-secondary text-sm py-3 flex items-center justify-center gap-2"
          >
            <Users size={18} />
            Hermanos
          </button>
          <button
            onClick={() => navigate('/api/admin/admins')}
            className="btn btn-secondary text-sm py-3 flex items-center justify-center gap-2"
          >
            <Users size={18} />
            Administradores
          </button>
          <button
            onClick={() => navigate('/api/admin/points')}
            className="btn btn-secondary text-sm py-3 flex items-center justify-center gap-2"
          >
            <MapPin size={18} />
            Exhibidores
          </button>
          <button
            onClick={() => navigate('/api/admin/reports')}
            className="btn btn-secondary text-sm py-3 flex items-center justify-center gap-2"
          >
            <BarChart3 size={18} />
            Reportes
          </button>
          <button
            onClick={handleLogout}
            className="btn bg-red-600 text-white hover:bg-red-700 text-sm py-3 col-span-2 lg:col-span-2 flex items-center justify-center gap-2"
          >
            <XCircle size={18} />
            Cerrar Sesión
          </button>
        </div>
      </header>

      {/* Availability Summary - Corregido */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-green-800 text-lg">Disponibles</h3>
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <p className="text-4xl font-bold text-green-700 mb-1">{availabilitySummary.available}</p>
          <p className="text-sm text-green-600">turno{availabilitySummary.available !== 1 ? 's' : ''} disponible{availabilitySummary.available !== 1 ? 's' : ''}</p>
        </div>

        <div className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-blue-800 text-lg">Asignados</h3>
            <Clock className="h-8 w-8 text-blue-600" />
          </div>
          <p className="text-4xl font-bold text-blue-700 mb-1">{availabilitySummary.occupied}</p>
          <p className="text-sm text-blue-600">turno{availabilitySummary.occupied !== 1 ? 's' : ''} asignado{availabilitySummary.occupied !== 1 ? 's' : ''}</p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold text-purple-800 text-lg">Total Sistema</h3>
            <BarChart3 className="h-8 w-8 text-purple-600" />
          </div>
          <p className="text-4xl font-bold text-purple-700 mb-1">{availabilitySummary.total}</p>
          <p className="text-sm text-purple-600">
            {availabilitySummary.total > 0
              ? Math.round((availabilitySummary.occupied / availabilitySummary.total) * 100)
              : 0}% de ocupación
          </p>
        </div>
      </div>

      {/* Status Filters - Con contadores */}
      <div className="card mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="h-5 w-5 text-primary-600" />
          <h3 className="font-bold text-lg">Estado de Turnos</h3>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setFilter('approved')}
            className={`px-6 py-3 rounded-lg font-medium transition-all flex items-center gap-2 ${
              filter === 'approved'
                ? 'bg-green-600 text-white shadow-lg scale-105'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <CheckCircle size={18} />
            Asignados ({requestCounts.approved || requests.length})
          </button>
          <button
            onClick={() => setFilter('cancelled')}
            className={`px-6 py-3 rounded-lg font-medium transition-all flex items-center gap-2 ${
              filter === 'cancelled'
                ? 'bg-orange-600 text-white shadow-lg scale-105'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <Unlock size={18} />
            Liberados ({requestCounts.cancelled || 0})
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card mb-6">
        <div className="flex items-center gap-2 mb-4">
          <Search className="h-5 w-5 text-primary-600" />
          <h3 className="font-bold text-lg">Búsqueda y Filtros</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Search by name or phone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Buscar por nombre o teléfono
            </label>
            <input
              type="text"
              placeholder="Escriba nombre o teléfono..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input w-full"
            />
          </div>
          
          {/* Filter by exhibitor */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filtrar por exhibidor
            </label>
            <select
              value={exhibitorFilter}
              onChange={(e) => setExhibitorFilter(e.target.value)}
              className="input w-full"
            >
              <option value="">Todos los exhibidores</option>
              {exhibitors.map(exhibitor => (
                <option key={exhibitor.id} value={exhibitor.id}>
                  {exhibitor.code ? `[${exhibitor.code}] ` : ''}{exhibitor.name}
                </option>
              ))}
            </select>
          </div>
          
          {/* Filter by date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filtrar por fecha
            </label>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="input w-full"
            />
          </div>
        </div>
        
        {/* Clear filters button */}
        {(searchTerm || exhibitorFilter || dateFilter) && (
          <div className="mt-4">
            <button
              onClick={() => {
                setSearchTerm('')
                setExhibitorFilter('')
                setDateFilter('')
              }}
              className="btn bg-gray-500 text-white hover:bg-gray-600 text-sm"
            >
              Limpiar Filtros
            </button>
          </div>
        )}
      </div>

      {/* Turnos por Mes */}
      {monthlyStats.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="h-5 w-5 text-primary-600" />
            <h3 className="font-bold text-lg">Turnos por Mes (Últimos 12 meses)</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 border-b">
                  <th className="px-4 py-2 text-left font-bold">Mes</th>
                  <th className="px-4 py-2 text-center font-bold text-blue-600">Asignados</th>
                  <th className="px-4 py-2 text-center font-bold text-green-600">Tomados</th>
                  <th className="px-4 py-2 text-center font-bold text-orange-600">Libres</th>
                </tr>
              </thead>
              <tbody>
                {monthlyStats.map((stat, idx) => (
                  <tr key={idx} className="border-b hover:bg-blue-50">
                    <td className="px-4 py-3 font-medium">{stat.month}</td>
                    <td className="px-4 py-3 text-center text-blue-700 font-bold">{stat.assigned}</td>
                    <td className="px-4 py-3 text-center text-green-700 font-bold">{stat.taken}</td>
                    <td className="px-4 py-3 text-center text-orange-700 font-bold">{stat.free}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Hermanos por Cantidad de Turnos */}
      {hermanoStats.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="h-5 w-5 text-primary-600" />
            <h3 className="font-bold text-lg">Hermanos - Ranking de Turnos</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 border-b">
                  <th className="px-4 py-2 text-left font-bold">Posición</th>
                  <th className="px-4 py-2 text-left font-bold">Nombre</th>
                  <th className="px-4 py-2 text-left font-bold">Teléfono</th>
                  <th className="px-4 py-2 text-left font-bold">Congregación</th>
                  <th className="px-4 py-2 text-center font-bold text-green-600">Turnos</th>
                </tr>
              </thead>
              <tbody>
                {hermanoStats.map((hermano, idx) => (
                  <tr key={hermano.id} className="border-b hover:bg-blue-50">
                    <td className="px-4 py-3 font-bold text-gray-700">
                      {((hermanoPagination.page - 1) * 50) + idx + 1}
                    </td>
                    <td className="px-4 py-3 font-medium">{hermano.nombre}</td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-xs">{hermano.telefono}</td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{hermano.congregacion || '-'}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full font-bold text-sm">
                        {hermano.turns_count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Paginación */}
          {hermanoPagination.total_pages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-600">
                Mostrando {((hermanoPagination.page - 1) * 50) + 1} - {Math.min(hermanoPagination.page * 50, hermanoPagination.total)} de {hermanoPagination.total} hermanos
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setHermanoPage(Math.max(1, hermanoPage - 1))}
                  disabled={hermanoPage === 1}
                  className="btn btn-secondary text-sm disabled:opacity-50"
                >
                  ← Anterior
                </button>
                <span className="px-4 py-2 bg-gray-100 rounded-lg font-medium">
                  {hermanoPagination.page} / {hermanoPagination.total_pages}
                </span>
                <button
                  onClick={() => setHermanoPage(Math.min(hermanoPagination.total_pages, hermanoPage + 1))}
                  disabled={hermanoPage === hermanoPagination.total_pages}
                  className="btn btn-secondary text-sm disabled:opacity-50"
                >
                  Siguiente →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Results Count */}
      <div className="mb-4 bg-blue-50 border-2 border-blue-200 rounded-lg p-3">
        <p className="text-blue-800 font-medium">
          📊 Mostrando <strong>{filteredRows.length}</strong> turno{filteredRows.length !== 1 ? 's' : ''}
          {searchTerm || exhibitorFilter || dateFilter ? ' (filtrados)' : ''}
        </p>
      </div>

      {/* Requests Table */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
          <p className="text-gray-600 mt-4">Cargando turnos...</p>
        </div>
      ) : filteredRows.length === 0 ? (
        <div className="card text-center py-12">
          <AlertCircle className="mx-auto mb-4 text-gray-400" size={48} />
          {requests.length === 0 ? (
            <div>
              <p className="text-green-700 text-lg font-bold mb-2">
                ✅ Todos los turnos están asignados
              </p>
              <p className="text-gray-600 text-sm mb-4">
                Ocupación: {availabilitySummary.total > 0 ? Math.round((availabilitySummary.occupied / availabilitySummary.total) * 100) : 0}% ({availabilitySummary.occupied} de {availabilitySummary.total})
              </p>
              <p className="text-gray-500 text-sm mb-4">
                💡 Ver tab "{filter === 'approved' ? 'Liberados' : 'Asignados'}" si necesita redistribuir turnos
              </p>
              {filter === 'approved' && (
                <button
                  onClick={() => setFilter('cancelled')}
                  className="btn btn-secondary"
                >
                  Ver Turnos Liberados
                </button>
              )}
            </div>
          ) : (
            <div>
              <p className="text-gray-600 text-lg font-medium mb-2">
                No se encontraron resultados con los filtros aplicados
              </p>
              <button
                onClick={() => {
                  setSearchTerm('')
                  setExhibitorFilter('')
                  setDateFilter('')
                }}
                className="btn btn-secondary mt-4"
              >
                Limpiar Filtros
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gradient-to-r from-primary-600 to-primary-700 text-white">
                <th className="px-4 py-4 text-left text-sm font-bold">Exhibidor</th>
                <th className="px-4 py-4 text-left text-sm font-bold">Fecha</th>
                <th className="px-4 py-4 text-left text-sm font-bold">Horario</th>
                <th className="px-4 py-4 text-left text-sm font-bold">Solicitante</th>
                <th className="px-4 py-4 text-left text-sm font-bold">Teléfono</th>
                <th className="px-4 py-4 text-left text-sm font-bold">Estado</th>
                {filter === 'approved' && (
                  <th className="px-4 py-4 text-left text-sm font-bold">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, idx) => (
                <tr key={`${row.request_id}-${row.id}-${idx}`} className="border-b border-gray-200 hover:bg-blue-50 transition-colors">
                  <td className="px-4 py-4">
                    <div className="font-medium text-gray-900">{row.point_name}</div>
                    {row.point_code && (
                      <div className="text-xs text-gray-500 font-mono">{row.point_code}</div>
                    )}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <Calendar size={16} className="text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">{row.date}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <Clock size={16} className="text-gray-400" />
                      <span className="text-sm font-medium text-gray-700">{row.schedule}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm font-medium text-gray-900">{row.applicant_name}</td>
                  <td className="px-4 py-4 text-sm text-gray-700">{row.applicant_phone}</td>
                  <td className="px-4 py-4">
                    <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${
                      row.status === 'approved' ? 'bg-green-100 text-green-800 border border-green-300' :
                      row.status === 'cancelled' ? 'bg-orange-100 text-orange-800 border border-orange-300' :
                      'bg-gray-100 text-gray-800 border border-gray-300'
                    }`}>
                      {row.status === 'approved' ? '✓ Aprobado' : 
                       row.status === 'cancelled' ? '○ Liberado' : 
                       row.status}
                    </span>
                  </td>
                  {filter === 'approved' && (
                    <td className="px-4 py-4">
                      <button
                        onClick={() => handleLiberarTurno(row.request_id, row.id)}
                        className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-all text-sm font-medium flex items-center gap-2 shadow-sm hover:shadow-md"
                        title="Liberar turno - El espacio quedará disponible"
                      >
                        <Unlock size={16} />
                        Liberar
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
    </div>
  )
}
