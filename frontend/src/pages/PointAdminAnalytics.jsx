import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, AlertCircle, Calendar, Loader } from 'lucide-react'
import client from '../api/client'
import { DailyOccupancyChart, WeeklyRequestsChart } from '../components/OccupancyChart'

export default function PointAdminAnalytics() {
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')

  // Analytics
  const [dailyOccupancy, setDailyOccupancy] = useState(null)
  const [weeklyRequests, setWeeklyRequests] = useState(null)
  const [auditTrail, setAuditTrail] = useState([])
  const [notifications, setNotifications] = useState(null)

  // Filters
  const [occupancyDays, setOccupancyDays] = useState(30)
  const [weeksShown, setWeeksShown] = useState(4)
  const [auditPage, setAuditPage] = useState(1)

  // Loading states
  const [loading, setLoading] = useState(true)
  const [loadingOccupancy, setLoadingOccupancy] = useState(false)
  const [loadingRequests, setLoadingRequests] = useState(false)
  const [loadingAudit, setLoadingAudit] = useState(false)

  useEffect(() => {
    if (!token) {
      navigate('/point-admin/login')
      return
    }
    loadAllAnalytics()
  }, [token])

  const loadAllAnalytics = async () => {
    try {
      setLoading(true)
      await Promise.all([
        loadNotifications(),
        loadOccupancy(30),
        loadWeeklyRequests(4),
        loadAuditTrail(1)
      ])
    } finally {
      setLoading(false)
    }
  }

  const loadNotifications = async () => {
    try {
      const response = await client.get('/api/point-admin/notifications/summary', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setNotifications(response.data)
    } catch (err) {
      console.error('Error loading notifications:', err)
    }
  }

  const loadOccupancy = async (days) => {
    try {
      setLoadingOccupancy(true)
      const response = await client.get(`/api/point-admin/analytics/occupancy-daily?days=${days}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setDailyOccupancy(response.data)
    } catch (err) {
      console.error('Error loading occupancy:', err)
    } finally {
      setLoadingOccupancy(false)
    }
  }

  const loadWeeklyRequests = async (weeks) => {
    try {
      setLoadingRequests(true)
      const response = await client.get(`/api/point-admin/analytics/requests-weekly?weeks=${weeks}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setWeeklyRequests(response.data)
    } catch (err) {
      console.error('Error loading requests:', err)
    } finally {
      setLoadingRequests(false)
    }
  }

  const loadAuditTrail = async (page) => {
    try {
      setLoadingAudit(true)
      const response = await client.get(`/api/point-admin/audit-trail?days=30&page=${page}&limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setAuditTrail(response.data)
    } catch (err) {
      console.error('Error loading audit trail:', err)
    } finally {
      setLoadingAudit(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-primary-600" />
            <h1 className="text-2xl font-bold text-gray-800">Analíticas y Auditoría</h1>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Notifications */}
        {notifications && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {notifications.alerts.map((alert) => (
              <div
                key={alert.type}
                className={`rounded-lg p-4 flex items-start gap-3 ${
                  alert.count > 0
                    ? 'bg-yellow-50 border border-yellow-200'
                    : 'bg-green-50 border border-green-200'
                }`}
              >
                <AlertCircle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                  alert.count > 0 ? 'text-yellow-600' : 'text-green-600'
                }`} />
                <div>
                  <p className={`text-sm font-medium ${
                    alert.count > 0 ? 'text-yellow-800' : 'text-green-800'
                  }`}>
                    {alert.message}
                  </p>
                  <p className={`text-2xl font-bold mt-2 ${
                    alert.count > 0 ? 'text-yellow-600' : 'text-green-600'
                  }`}>
                    {alert.count}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Daily Occupancy Chart */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Ocupación por Día</h2>
            <select
              value={occupancyDays}
              onChange={(e) => {
                const days = parseInt(e.target.value)
                setOccupancyDays(days)
                loadOccupancy(days)
              }}
              className="px-3 py-2 border border-gray-300 rounded text-sm"
            >
              <option value={7}>Últimos 7 días</option>
              <option value={14}>Últimas 2 semanas</option>
              <option value={30}>Último mes</option>
              <option value={90}>Últimos 3 meses</option>
            </select>
          </div>
          {loadingOccupancy ? (
            <div className="text-center py-8">
              <Loader className="w-6 h-6 animate-spin mx-auto text-primary-600" />
            </div>
          ) : (
            <DailyOccupancyChart data={dailyOccupancy?.data} />
          )}
          {dailyOccupancy && (
            <p className="text-sm text-gray-600 mt-4">
              Ocupación promedio: <strong>{dailyOccupancy.average_occupancy}%</strong>
            </p>
          )}
        </div>

        {/* Weekly Requests Chart */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">Solicitudes Semanales</h2>
            <select
              value={weeksShown}
              onChange={(e) => {
                const weeks = parseInt(e.target.value)
                setWeeksShown(weeks)
                loadWeeklyRequests(weeks)
              }}
              className="px-3 py-2 border border-gray-300 rounded text-sm"
            >
              <option value={4}>Últimas 4 semanas</option>
              <option value={8}>Últimas 8 semanas</option>
              <option value={12}>Últimas 12 semanas</option>
            </select>
          </div>
          {loadingRequests ? (
            <div className="text-center py-8">
              <Loader className="w-6 h-6 animate-spin mx-auto text-primary-600" />
            </div>
          ) : (
            <WeeklyRequestsChart data={weeklyRequests?.data} />
          )}
        </div>

        {/* Audit Trail */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-800">Registro de Auditoría</h2>
            </div>
            <p className="text-sm text-gray-600 mt-2">Últimos 30 días</p>
          </div>

          {loadingAudit ? (
            <div className="text-center py-8">
              <Loader className="w-6 h-6 animate-spin mx-auto text-primary-600" />
            </div>
          ) : auditTrail.data?.length === 0 ? (
            <p className="p-6 text-gray-500 text-center">Sin registros</p>
          ) : (
            <div className="divide-y">
              {auditTrail.data?.map((log) => (
                <div key={log.id} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-medium text-gray-800">{log.action}</p>
                      <p className="text-sm text-gray-600">{log.entity_type}</p>
                    </div>
                    <time className="text-xs text-gray-500">
                      {new Date(log.created_at).toLocaleString('es-CO')}
                    </time>
                  </div>
                  {log.details && (
                    <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded mt-2">
                      <code>{JSON.stringify(log.details, null, 2)}</code>
                    </div>
                  )}
                </div>
              ))}

              {/* Pagination */}
              {auditTrail.pagination && auditTrail.pagination.total_pages > 1 && (
                <div className="p-4 flex justify-center gap-2">
                  <button
                    onClick={() => loadAuditTrail(auditPage - 1)}
                    disabled={auditPage === 1}
                    className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <span className="px-4 py-2">
                    Página {auditPage} de {auditTrail.pagination.total_pages}
                  </span>
                  <button
                    onClick={() => loadAuditTrail(auditPage + 1)}
                    disabled={auditPage === auditTrail.pagination.total_pages}
                    className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                  >
                    Siguiente
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
