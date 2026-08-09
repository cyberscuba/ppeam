import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Download, Calendar, ArrowLeft, TrendingUp, Users, FileText, 
  BarChart3, PieChart, Activity, AlertCircle, CheckCircle2, XCircle
} from 'lucide-react'
import client from '../api/client'
import NotificationModal from '../components/NotificationModal'

export default function AdminReportsPage() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [loading, setLoading] = useState(false)
  const [dashboardStats, setDashboardStats] = useState(null)
  const [loadingStats, setLoadingStats] = useState(false)
  const [notification, setNotification] = useState(null)
  const navigate = useNavigate()

  // Establecer fechas por defecto (mes actual)
  useEffect(() => {
    const today = new Date()
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
    setStartDate(firstDay.toISOString().split('T')[0])
    setEndDate(today.toISOString().split('T')[0])
  }, [])

  // Cargar estadísticas cuando cambian las fechas
  useEffect(() => {
    if (startDate && endDate) {
      loadDashboardStats()
    }
  }, [startDate, endDate])

  const loadDashboardStats = async () => {
    setLoadingStats(true)
    try {
      const { data } = await client.get('/api/admin/reports/dashboard', {
        params: { start_date: startDate, end_date: endDate }
      })
      setDashboardStats(data)
    } catch (error) {
      console.error('Error loading dashboard stats:', error)
      setNotification({
        type: 'error',
        title: 'Error al Cargar Estadísticas',
        message: 'No se pudieron cargar las estadísticas del dashboard.',
        details: [error.response?.data?.detail || error.message]
      })
    } finally {
      setLoadingStats(false)
    }
  }

  const downloadReport = async (type) => {
    if (!startDate || !endDate) {
      setNotification({
        type: 'warning',
        title: 'Fechas Requeridas',
        message: 'Por favor seleccione el rango de fechas para el reporte.',
        details: []
      })
      return
    }

    setLoading(true)
    try {
      const response = await client.get(`/api/admin/reports/${type}`, {
        params: { start_date: startDate, end_date: endDate },
        responseType: 'blob'
      })

      // Crear link de descarga
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `reporte_${type}_${startDate}_${endDate}.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()

      setNotification({
        type: 'success',
        title: '¡Reporte Generado!',
        message: 'El reporte se ha descargado exitosamente.',
        details: [`Archivo: reporte_${type}_${startDate}_${endDate}.xlsx`]
      })
    } catch (error) {
      setNotification({
        type: 'error',
        title: 'Error al Generar Reporte',
        message: 'No se pudo generar el reporte solicitado.',
        details: [error.response?.data?.detail || error.message]
      })
    } finally {
      setLoading(false)
    }
  }

  const setQuickDateRange = (range) => {
    const today = new Date()
    let start, end

    switch (range) {
      case 'today':
        start = end = today
        break
      case 'week':
        start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 7)
        end = today
        break
      case 'month':
        start = new Date(today.getFullYear(), today.getMonth(), 1)
        end = today
        break
      case 'last_month':
        start = new Date(today.getFullYear(), today.getMonth() - 1, 1)
        end = new Date(today.getFullYear(), today.getMonth(), 0)
        break
      case 'year':
        start = new Date(today.getFullYear(), 0, 1)
        end = today
        break
      default:
        return
    }

    setStartDate(start.toISOString().split('T')[0])
    setEndDate(end.toISOString().split('T')[0])
  }

  const StatCard = ({ icon: Icon, title, value, subtitle, color = "blue", trend }) => (
    <div className={`bg-gradient-to-br from-${color}-50 to-${color}-100 border-2 border-${color}-200 rounded-xl p-6 shadow-md hover:shadow-lg transition-all`}>
      <div className="flex items-start justify-between mb-3">
        <div className={`p-3 bg-${color}-500 rounded-lg`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
        {trend && (
          <div className={`text-xs font-semibold px-2 py-1 rounded-full ${trend > 0 ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
          </div>
        )}
      </div>
      <h3 className="text-gray-600 text-sm font-medium mb-1">{title}</h3>
      <p className={`text-3xl font-bold text-${color}-700 mb-1`}>{value}</p>
      {subtitle && <p className="text-gray-500 text-xs">{subtitle}</p>}
    </div>
  )

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* Header */}
      <header className="mb-8">
        <button
          onClick={() => navigate('/admin')}
          className="btn btn-secondary mb-4 flex items-center gap-2"
        >
          <ArrowLeft size={20} />
          Volver
        </button>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center gap-3">
              📊 Reportes y Estadísticas
            </h1>
            <p className="text-gray-600 text-lg">
              Dashboard de análisis y reportes descargables
            </p>
          </div>
          <BarChart3 className="h-16 w-16 text-primary-500 opacity-20" />
        </div>
      </header>

      {/* Date Range Selector */}
      <div className="card mb-8 bg-gradient-to-r from-gray-50 to-gray-100">
        <div className="flex items-center gap-3 mb-4">
          <Calendar className="h-6 w-6 text-primary-600" />
          <h2 className="text-2xl font-bold">Rango de Fechas</h2>
        </div>
        
        {/* Quick Range Buttons */}
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={() => setQuickDateRange('today')}
            className="px-4 py-2 bg-white border-2 border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-sm font-medium"
          >
            Hoy
          </button>
          <button
            onClick={() => setQuickDateRange('week')}
            className="px-4 py-2 bg-white border-2 border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-sm font-medium"
          >
            Última Semana
          </button>
          <button
            onClick={() => setQuickDateRange('month')}
            className="px-4 py-2 bg-white border-2 border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-sm font-medium"
          >
            Este Mes
          </button>
          <button
            onClick={() => setQuickDateRange('last_month')}
            className="px-4 py-2 bg-white border-2 border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-sm font-medium"
          >
            Mes Anterior
          </button>
          <button
            onClick={() => setQuickDateRange('year')}
            className="px-4 py-2 bg-white border-2 border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-sm font-medium"
          >
            Este Año
          </button>
        </div>

        {/* Custom Date Inputs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-gray-700 font-medium mb-2">
              📅 Fecha Inicio
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="input w-full"
              required
            />
          </div>

          <div>
            <label className="block text-gray-700 font-medium mb-2">
              📅 Fecha Fin
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="input w-full"
              required
            />
          </div>
        </div>

        {startDate && endDate && (
          <div className="bg-primary-50 border-2 border-primary-200 rounded-lg p-4 mt-4">
            <p className="text-primary-800 font-medium">
              📊 Mostrando datos desde <strong>{startDate}</strong> hasta <strong>{endDate}</strong>
            </p>
          </div>
        )}
      </div>

      {/* Dashboard Statistics */}
      {loadingStats ? (
        <div className="card mb-8 text-center py-12">
          <Activity className="h-12 w-12 text-primary-600 mx-auto mb-4 animate-pulse" />
          <p className="text-gray-600 text-lg">Cargando estadísticas...</p>
        </div>
      ) : dashboardStats && (
        <>
          {/* Main Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard
              icon={FileText}
              title="Total Solicitudes"
              value={dashboardStats.total_requests}
              subtitle="En el periodo seleccionado"
              color="blue"
            />
            <StatCard
              icon={CheckCircle2}
              title="Turnos Aprobados"
              value={dashboardStats.approved_requests}
              subtitle={`${Math.round((dashboardStats.approved_requests / dashboardStats.total_requests) * 100) || 0}% del total`}
              color="green"
            />
            <StatCard
              icon={XCircle}
              title="Turnos Liberados"
              value={dashboardStats.cancelled_requests}
              subtitle={`${Math.round((dashboardStats.cancelled_requests / dashboardStats.total_requests) * 100) || 0}% del total`}
              color="red"
            />
            <StatCard
              icon={TrendingUp}
              title="Tasa de Ocupación"
              value={`${dashboardStats.occupancy_rate}%`}
              subtitle={`${dashboardStats.occupied_slots} de ${dashboardStats.total_slots} slots`}
              color="purple"
            />
          </div>

          {/* Secondary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <StatCard
              icon={Activity}
              title="Exhibidores Activos"
              value={dashboardStats.active_exhibitors}
              subtitle={`de ${dashboardStats.total_exhibitors} totales`}
              color="orange"
            />
            <StatCard
              icon={Users}
              title="Usuarios Activos"
              value={dashboardStats.active_users}
              subtitle={`de ${dashboardStats.total_users} totales`}
              color="cyan"
            />
            <StatCard
              icon={BarChart3}
              title="Promedio por Usuario"
              value={dashboardStats.active_users > 0 ? Math.round(dashboardStats.approved_requests / dashboardStats.active_users * 10) / 10 : 0}
              subtitle="Turnos por usuario"
              color="indigo"
            />
          </div>

          {/* Highlights */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Most Requested */}
            {dashboardStats.most_requested_exhibitor && (
              <div className="card bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200">
                <h3 className="text-xl font-bold text-green-800 mb-3 flex items-center gap-2">
                  🏆 Exhibidor Más Solicitado
                </h3>
                <p className="text-2xl font-bold text-green-700 mb-1">
                  {dashboardStats.most_requested_exhibitor.name}
                </p>
                <p className="text-green-600">
                  {dashboardStats.most_requested_exhibitor.count} solicitudes
                </p>
              </div>
            )}

            {/* Peak Day */}
            {dashboardStats.peak_day && (
              <div className="card bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200">
                <h3 className="text-xl font-bold text-purple-800 mb-3 flex items-center gap-2">
                  📈 Día Pico de Solicitudes
                </h3>
                <p className="text-2xl font-bold text-purple-700 mb-1">
                  {new Date(dashboardStats.peak_day.date).toLocaleDateString('es-ES', { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </p>
                <p className="text-purple-600">
                  {dashboardStats.peak_day.count} solicitudes
                </p>
              </div>
            )}
          </div>

          {/* Top Exhibitors */}
          {dashboardStats.requests_by_exhibitor.length > 0 && (
            <div className="card mb-8">
              <h3 className="text-2xl font-bold mb-4 flex items-center gap-2">
                <PieChart className="h-6 w-6 text-primary-600" />
                Top 10 Exhibidores por Solicitudes
              </h3>
              <div className="space-y-3">
                {dashboardStats.requests_by_exhibitor.map((exhibitor, index) => {
                  const maxCount = dashboardStats.requests_by_exhibitor[0].count
                  const percentage = (exhibitor.count / maxCount) * 100
                  
                  return (
                    <div key={exhibitor.id} className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-gray-800">
                            {exhibitor.code ? `[${exhibitor.code}] ` : ''}{exhibitor.name}
                          </span>
                          <span className="font-bold text-primary-700">{exhibitor.count}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-primary-600 h-2 rounded-full transition-all"
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}

      {/* Reports Download Section */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <Download className="h-6 w-6 text-primary-600" />
          Reportes Descargables (Excel)
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Requests Report */}
          <div className="card hover:shadow-xl transition-all border-2 border-transparent hover:border-primary-300">
            <div className="flex items-center gap-3 mb-3">
              <FileText className="h-8 w-8 text-blue-600" />
              <h3 className="text-xl font-bold">Solicitudes Detalladas</h3>
            </div>
            <p className="text-gray-600 mb-4 text-sm">
              Todas las solicitudes con usuario, exhibidor, fecha, horarios y estado
            </p>
            <button
              onClick={() => downloadReport('requests')}
              disabled={loading || !startDate || !endDate}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Download size={20} />
              {loading ? 'Generando...' : 'Descargar'}
            </button>
          </div>

          {/* Exhibitors Report */}
          <div className="card hover:shadow-xl transition-all border-2 border-transparent hover:border-green-300">
            <div className="flex items-center gap-3 mb-3">
              <Activity className="h-8 w-8 text-green-600" />
              <h3 className="text-xl font-bold">Análisis por Exhibidor</h3>
            </div>
            <p className="text-gray-600 mb-4 text-sm">
              Estadísticas completas de ocupación, capacidad y turnos por exhibidor
            </p>
            <button
              onClick={() => downloadReport('points')}
              disabled={loading || !startDate || !endDate}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Download size={20} />
              {loading ? 'Generando...' : 'Descargar'}
            </button>
          </div>

          {/* Users Report */}
          <div className="card hover:shadow-xl transition-all border-2 border-transparent hover:border-purple-300">
            <div className="flex items-center gap-3 mb-3">
              <Users className="h-8 w-8 text-purple-600" />
              <h3 className="text-xl font-bold">Actividad de Usuarios</h3>
            </div>
            <p className="text-gray-600 mb-4 text-sm">
              Historial completo de solicitudes y turnos por usuario
            </p>
            <button
              onClick={() => downloadReport('users')}
              disabled={loading || !startDate || !endDate}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Download size={20} />
              {loading ? 'Generando...' : 'Descargar'}
            </button>
          </div>

          {/* Schedules Report */}
          <div className="card hover:shadow-xl transition-all border-2 border-transparent hover:border-orange-300">
            <div className="flex items-center gap-3 mb-3">
              <Calendar className="h-8 w-8 text-orange-600" />
              <h3 className="text-xl font-bold">Horarios y Capacidad</h3>
            </div>
            <p className="text-gray-600 mb-4 text-sm">
              Detalle de todos los horarios con ocupación y disponibilidad
            </p>
            <button
              onClick={() => downloadReport('schedules')}
              disabled={loading || !startDate || !endDate}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Download size={20} />
              {loading ? 'Generando...' : 'Descargar'}
            </button>
          </div>

          {/* Capacity Report */}
          <div className="card hover:shadow-xl transition-all border-2 border-transparent hover:border-red-300">
            <div className="flex items-center gap-3 mb-3">
              <BarChart3 className="h-8 w-8 text-red-600" />
              <h3 className="text-xl font-bold">Análisis de Capacidad</h3>
            </div>
            <p className="text-gray-600 mb-4 text-sm">
              Reporte de capacidad total, ocupación y disponibilidad del sistema
            </p>
            <button
              onClick={() => downloadReport('capacity')}
              disabled={loading || !startDate || !endDate}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Download size={20} />
              {loading ? 'Generando...' : 'Descargar'}
            </button>
          </div>

          {/* Liberated by User Report */}
          <div className="card hover:shadow-xl transition-all border-2 border-transparent hover:border-yellow-300">
            <div className="flex items-center gap-3 mb-3">
              <XCircle className="h-8 w-8 text-yellow-600" />
              <h3 className="text-xl font-bold">Turnos Liberados por Usuario</h3>
            </div>
            <p className="text-gray-600 mb-4 text-sm">
              Reporte de cantidad de veces que cada hermano ha pedido liberar turnos, con detalles de cada liberación
            </p>
            <button
              onClick={() => downloadReport('cancelled-by-user')}
              disabled={loading}
              className="btn btn-primary w-full flex items-center justify-center gap-2"
            >
              <Download size={20} />
              {loading ? 'Generando...' : 'Descargar'}
            </button>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="card bg-gradient-to-r from-blue-50 to-cyan-50 border-2 border-blue-200">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-6 w-6 text-blue-600 flex-shrink-0 mt-1" />
          <div>
            <h3 className="font-bold text-blue-900 mb-2">💡 Información sobre los Reportes</h3>
            <ul className="text-blue-800 text-sm space-y-1">
              <li>• Los reportes se generan en formato Excel (.xlsx) con formato profesional</li>
              <li>• Cada reporte incluye un resumen ejecutivo con estadísticas clave</li>
              <li>• Los datos se filtran automáticamente según el rango de fechas seleccionado</li>
              <li>• Los archivos incluyen filtros y formato para facilitar el análisis</li>
              <li>• El dashboard se actualiza automáticamente al cambiar las fechas</li>
            </ul>
          </div>
        </div>
      </div>

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
