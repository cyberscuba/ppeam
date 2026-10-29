import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, BarChart3, Users, Download, Trash2, AlertCircle, Loader } from 'lucide-react'
import client from '../api/client'

export default function PointAdminDashboard() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('stats')

  // Stats
  const [exhibitor, setExhibitor] = useState(null)
  const [stats, setStats] = useState(null)

  // Requests
  const [requests, setRequests] = useState([])
  const [requestsLoading, setRequestsLoading] = useState(false)
  const [requestsPage, setRequestsPage] = useState(1)
  const [requestsPagination, setRequestsPagination] = useState(null)

  // Hermanos list
  const [hermanosList, setHermanosList] = useState([])
  const [hermanosLoading, setHermanosLoading] = useState(false)
  const [hermanosPage, setHermanosPage] = useState(1)
  const [hermanosPagination, setHermanosPagination] = useState(null)

  // Release turn
  const [releasingId, setReleasingId] = useState(null)
  const [releaseReason, setReleaseReason] = useState('')
  const [releaseError, setReleaseError] = useState(null)

  const token = localStorage.getItem('access_token')
  const exhibitorId = localStorage.getItem('exhibitor_id')
  const position = localStorage.getItem('position')

  useEffect(() => {
    if (!token || !exhibitorId) {
      navigate('/point-admin/login')
      return
    }
    loadDashboard()
  }, [token, exhibitorId])

  const loadDashboard = async () => {
    try {
      setLoading(true)
      const response = await client.get('/api/point-admin/dashboard', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setExhibitor(response.data.exhibitor)
      setStats(response.data.stats)
    } catch (err) {
      console.error('Error loading dashboard:', err)
      if (err.response?.status === 401) {
        navigate('/point-admin/login')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadRequests = async (page = 1) => {
    try {
      setRequestsLoading(true)
      const response = await client.get(`/api/point-admin/requests?page=${page}&limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setRequests(response.data.data)
      setRequestsPagination(response.data.pagination)
      setRequestsPage(page)
    } catch (err) {
      console.error('Error loading requests:', err)
    } finally {
      setRequestsLoading(false)
    }
  }

  const loadHermanos = async (page = 1) => {
    try {
      setHermanosLoading(true)
      const response = await client.get(`/api/point-admin/hermanos-request-list?page=${page}&limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setHermanosList(response.data.data)
      setHermanosPagination(response.data.pagination)
      setHermanosPage(page)
    } catch (err) {
      console.error('Error loading hermanos:', err)
    } finally {
      setHermanosLoading(false)
    }
  }

  const handleReleaseTurn = async (requestItemId) => {
    if (!releaseReason.trim()) {
      setReleaseError('Debe ingresar una razón')
      return
    }

    try {
      setReleasingId(requestItemId)
      await client.post(
        `/api/point-admin/release-turn/${requestItemId}?reason=${encodeURIComponent(releaseReason)}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      )
      setReleaseReason('')
      setReleaseError(null)
      alert('Turno liberado exitosamente')
      await loadRequests(requestsPage)
    } catch (err) {
      setReleaseError(err.response?.data?.detail || 'Error al liberar el turno')
    } finally {
      setReleasingId(null)
    }
  }

  const handleExport = async (format) => {
    try {
      const response = await client.get(`/api/point-admin/export?format=${format}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: format === 'csv' ? 'text' : 'json'
      })

      if (format === 'csv') {
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `punto_${exhibitorId}_${new Date().toISOString().split('T')[0]}.csv`)
        document.body.appendChild(link)
        link.click()
        link.parentChild?.removeChild(link)
      } else {
        const dataStr = JSON.stringify(response.data, null, 2)
        const url = window.URL.createObjectURL(new Blob([dataStr]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `punto_${exhibitorId}_${new Date().toISOString().split('T')[0]}.json`)
        document.body.appendChild(link)
        link.click()
        link.parentChild?.removeChild(link)
      }
    } catch (err) {
      alert('Error al exportar datos')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('admin_type')
    localStorage.removeItem('exhibitor_id')
    localStorage.removeItem('position')
    navigate('/point-admin/login')
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
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">
              {exhibitor?.name || 'Punto de Acopio'}
            </h1>
            <p className="text-sm text-gray-600">
              Encargado {position === 'principal' ? 'Principal' : 'Suplente'}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            <LogOut className="w-4 h-4" />
            Cerrar Sesión
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-600 text-sm mb-2">Turnos Totales</p>
              <p className="text-3xl font-bold text-gray-800">{stats.total_slots}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-600 text-sm mb-2">Disponibles</p>
              <p className="text-3xl font-bold text-green-600">{stats.available_slots}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-600 text-sm mb-2">Tomados</p>
              <p className="text-3xl font-bold text-blue-600">{stats.taken_slots}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-gray-600 text-sm mb-2">Ocupación</p>
              <p className="text-3xl font-bold text-purple-600">{stats.occupancy_percent}%</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow">
          <div className="border-b flex">
            <button
              onClick={() => {
                setActiveTab('stats')
                loadDashboard()
              }}
              className={`flex items-center gap-2 px-6 py-4 font-medium ${
                activeTab === 'stats'
                  ? 'border-b-2 border-primary-600 text-primary-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              Resumen
            </button>
            <button
              onClick={() => {
                setActiveTab('requests')
                loadRequests()
              }}
              className={`flex items-center gap-2 px-6 py-4 font-medium ${
                activeTab === 'requests'
                  ? 'border-b-2 border-primary-600 text-primary-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Users className="w-4 h-4" />
              Turnos Solicitados
            </button>
            <button
              onClick={() => {
                setActiveTab('hermanos')
                loadHermanos()
              }}
              className={`flex items-center gap-2 px-6 py-4 font-medium ${
                activeTab === 'hermanos'
                  ? 'border-b-2 border-primary-600 text-primary-600'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              <Users className="w-4 h-4" />
              Hermanos
            </button>
          </div>

          <div className="p-6">
            {/* Requests Tab */}
            {activeTab === 'requests' && (
              <div>
                <div className="flex justify-end mb-4">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleExport('csv')}
                      className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                    >
                      <Download className="w-4 h-4" />
                      CSV
                    </button>
                    <button
                      onClick={() => handleExport('json')}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      <Download className="w-4 h-4" />
                      JSON
                    </button>
                  </div>
                </div>

                {releaseError && (
                  <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <p className="text-red-700 text-sm">{releaseError}</p>
                  </div>
                )}

                {requestsLoading ? (
                  <div className="text-center py-8">
                    <Loader className="w-6 h-6 animate-spin mx-auto text-primary-600" />
                  </div>
                ) : requests.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No hay solicitudes</p>
                ) : (
                  <div className="space-y-4">
                    {requests.map((req) => (
                      <div key={req.id} className="border rounded-lg p-4">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <p className="font-bold text-gray-800">{req.hermano.nombre}</p>
                            <p className="text-sm text-gray-600">{req.hermano.telefono}</p>
                            <p className="text-sm text-gray-600">{req.hermano.congregacion}</p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                            req.status === 'approved'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {req.status === 'approved' ? 'Aprobado' : 'Pendiente'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mb-3">
                          {req.turns_requested} turno{req.turns_requested !== 1 ? 's' : ''} solicitado{req.turns_requested !== 1 ? 's' : ''}
                        </p>

                        {req.status === 'approved' && (
                          <div className="mt-4 space-y-2 border-t pt-4">
                            <input
                              type="text"
                              placeholder="Razón para liberar el turno..."
                              value={releaseReason}
                              onChange={(e) => setReleaseReason(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                            />
                            <button
                              onClick={() => handleReleaseTurn(req.turns[0]?.id)}
                              disabled={releasingId === req.turns[0]?.id}
                              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-400"
                            >
                              <Trash2 className="w-4 h-4" />
                              {releasingId === req.turns[0]?.id ? 'Liberando...' : 'Liberar Turno'}
                            </button>
                          </div>
                        )}
                      </div>
                    ))}

                    {/* Pagination */}
                    {requestsPagination && requestsPagination.total_pages > 1 && (
                      <div className="flex justify-center gap-2 mt-6">
                        <button
                          onClick={() => loadRequests(requestsPage - 1)}
                          disabled={requestsPage === 1}
                          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                        >
                          Anterior
                        </button>
                        <span className="px-4 py-2">
                          Página {requestsPage} de {requestsPagination.total_pages}
                        </span>
                        <button
                          onClick={() => loadRequests(requestsPage + 1)}
                          disabled={requestsPage === requestsPagination.total_pages}
                          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                        >
                          Siguiente
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Hermanos Tab */}
            {activeTab === 'hermanos' && (
              <div>
                {hermanosLoading ? (
                  <div className="text-center py-8">
                    <Loader className="w-6 h-6 animate-spin mx-auto text-primary-600" />
                  </div>
                ) : hermanosList.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No hay hermanos registrados</p>
                ) : (
                  <div className="space-y-3">
                    {hermanosList.map((h, idx) => (
                      <div key={h.id} className="flex justify-between items-start border rounded p-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-gray-800">#{(hermanosPage - 1) * 20 + idx + 1}</span>
                            <p className="font-bold text-gray-800">{h.nombre}</p>
                          </div>
                          <p className="text-sm text-gray-600">{h.telefono}</p>
                          <p className="text-sm text-gray-600">{h.congregacion}</p>
                        </div>
                        <div className="bg-primary-100 text-primary-800 px-3 py-1 rounded-full font-bold">
                          {h.request_count} turno{h.request_count !== 1 ? 's' : ''}
                        </div>
                      </div>
                    ))}

                    {/* Pagination */}
                    {hermanosPagination && hermanosPagination.total_pages > 1 && (
                      <div className="flex justify-center gap-2 mt-6">
                        <button
                          onClick={() => loadHermanos(hermanosPage - 1)}
                          disabled={hermanosPage === 1}
                          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                        >
                          Anterior
                        </button>
                        <span className="px-4 py-2">
                          Página {hermanosPage} de {hermanosPagination.total_pages}
                        </span>
                        <button
                          onClick={() => loadHermanos(hermanosPage + 1)}
                          disabled={hermanosPage === hermanosPagination.total_pages}
                          className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
                        >
                          Siguiente
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Stats Tab */}
            {activeTab === 'stats' && stats && (
              <div className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
                    <p className="text-green-700 text-sm font-medium mb-2">Disponibles</p>
                    <p className="text-3xl font-bold text-green-800">{stats.available_slots}</p>
                  </div>
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
                    <p className="text-blue-700 text-sm font-medium mb-2">Tomados</p>
                    <p className="text-3xl font-bold text-blue-800">{stats.taken_slots}</p>
                  </div>
                  <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
                    <p className="text-purple-700 text-sm font-medium mb-2">Ocupación</p>
                    <p className="text-3xl font-bold text-purple-800">{stats.occupancy_percent}%</p>
                  </div>
                  <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-4 rounded-lg">
                    <p className="text-gray-700 text-sm font-medium mb-2">Total</p>
                    <p className="text-3xl font-bold text-gray-800">{stats.total_slots}</p>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="text-blue-800 text-sm">
                    <strong>Solicitudes Aprobadas:</strong> {stats.approved_requests}
                  </p>
                  <p className="text-blue-800 text-sm">
                    <strong>Solicitudes Canceladas:</strong> {stats.cancelled_requests}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
