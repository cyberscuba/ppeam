import { useState, useEffect } from 'react'
import logger from '../utils/logger'
import { useNavigate } from 'react-router-dom'
import { Users, Search, UserPlus, Edit, Trash, ArrowLeft, Phone, MapPin, Calendar, Power } from 'lucide-react'
import client from '../api/client'
import ConfirmationModal from '../components/ConfirmationModal'

export default function AdminUsersPage() {
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [confirmationModal, setConfirmationModal] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const { data } = await client.get('/api/admin/hermanos')
      logger.log('Hermanos cargados:', data.length)
      setUsers(data)
    } catch (error) {
      logger.error('Error loading hermanos:', error)
      alert('Error al cargar hermanos: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const filteredUsers = users.filter(u =>
    u.nombre.toLowerCase().includes(search.toLowerCase()) ||
    u.telefono.includes(search) ||
    (u.congregacion && u.congregacion.toLowerCase().includes(search.toLowerCase()))
  )

  const handleSave = async (userData) => {
    try {
      if (editingUser) {
        await client.patch(`/api/admin/hermanos/${editingUser.id}`, userData)
      } else {
        await client.post('/api/admin/hermanos', userData)
      }
      setShowModal(false)
      setEditingUser(null)
      loadUsers()
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleToggleStatus = async (userId, currentStatus) => {
    try {
      await client.patch(`/api/admin/hermanos/${userId}`, {
        is_active: !currentStatus
      })
      loadUsers()
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleDelete = async (userId) => {
    setConfirmationModal({
      isOpen: true,
      title: '¿Eliminar Hermano?',
      message: '¿Está seguro de eliminar este hermano?',
      confirmText: 'Sí, Eliminar',
      cancelText: 'Cancelar',
      onConfirm: async () => {
        setConfirmationModal(null)
        try {
          await client.delete(`/api/admin/hermanos/${userId}`)
          loadUsers()
        } catch (error) {
          alert('Error: ' + (error.response?.data?.detail || error.message))
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
          className="btn btn-secondary mb-4 flex items-center gap-2"
        >
          <ArrowLeft size={20} />
          Volver
        </button>
        <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
              Gestión de Hermanos
            </h1>
            <p className="text-gray-600">
              {users.length} hermanos registrados
            </p>
          </div>
          <button
            onClick={() => { setEditingUser(null); setShowModal(true) }}
            className="btn btn-primary flex items-center gap-2 w-full md:w-auto"
          >
            <UserPlus size={20} />
            Nuevo Hermano(a)
          </button>
        </div>
      </header>

      {/* Search */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Buscar hermano(a) por nombre, teléfono o congregación..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-12"
          />
        </div>
      </div>

      {/* Users List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="card text-center py-12">
          <Users className="mx-auto mb-4 text-gray-400" size={48} />
          <p className="text-gray-600 text-lg">
            {search ? 'No se encontraron hermanos con ese criterio' : 'No hay hermanos registrados'}
          </p>
          {search && (
            <button
              onClick={() => setSearch('')}
              className="btn btn-secondary mt-4"
            >
              Limpiar búsqueda
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:gap-5">
          {filteredUsers.map((user) => (
            <div
              key={user.id}
              className="group border border-gray-100 bg-white rounded-lg shadow-sm hover:shadow-md hover:border-gray-200 transition-all duration-200"
            >
              {/* Contenedor principal */}
              <div className="flex flex-col md:flex-row md:items-start gap-0">
                {/* Sección principal: Avatar + Info */}
                <div className="flex-1 flex gap-4 p-6">
                  {/* Avatar circular con iniciales */}
                  <div className="flex-shrink-0">
                    <div className="h-14 w-14 rounded-full bg-gradient-to-br from-indigo-100 to-indigo-200 flex items-center justify-center ring-1 ring-indigo-300/50">
                      <span className="text-sm font-semibold text-indigo-700">
                        {user.nombre.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                      </span>
                    </div>
                  </div>

                  {/* Contenido textual */}
                  <div className="flex-1 min-w-0">
                    {/* Línea superior: Nombre + Estado + Tipo */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {user.nombre}
                      </h3>
                      <div className="flex items-center gap-3">
                        {/* Badge de estado */}
                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-md">
                          <span
                            className={`h-2 w-2 rounded-full ${
                              user.is_active ? 'bg-emerald-500' : 'bg-gray-400'
                            }`}
                          />
                          <span className={`text-xs font-medium ${
                            user.is_active ? 'text-emerald-700' : 'text-gray-600'
                          }`}>
                            {user.is_active ? 'Activo' : 'Inactivo'}
                          </span>
                        </div>

                        {/* Tipo de relación */}
                        <span className="inline-flex text-xs font-medium text-gray-600 px-2.5 py-1.5 bg-gray-50 rounded-md">
                          {user.gender_label || 'Hermano'}
                        </span>
                      </div>
                    </div>

                    {/* Grid de información: 2 columnas en desktop */}
                    <div className="grid grid-cols-2 gap-x-6 gap-y-3 mb-4">
                      {/* Teléfono */}
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-gray-500 uppercase tracking-0.5 mb-1">
                          Contacto
                        </p>
                        <div className="flex items-center gap-2 text-sm text-gray-700">
                          <Phone size={16} className="text-gray-400 flex-shrink-0" />
                          <span className="font-mono truncate">{user.telefono}</span>
                        </div>
                      </div>

                      {/* Congregación */}
                      {user.congregacion && (
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-0.5 mb-1">
                            Congregación
                          </p>
                          <div className="flex items-center gap-2 text-sm text-gray-700">
                            <MapPin size={16} className="text-gray-400 flex-shrink-0" />
                            <span className="truncate">{user.congregacion}</span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Fecha de registro - sutil */}
                    {user.created_at && (
                      <div className="flex items-center gap-1.5 text-xs text-gray-500">
                        <Calendar size={14} className="flex-shrink-0" />
                        <span>
                          Registrado el {new Date(user.created_at).toLocaleDateString('es-ES', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric'
                          })}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Sección de acciones - Derecha */}
                <div className="w-full md:w-auto flex md:flex-col gap-2 px-6 pb-6 md:pb-6 md:pr-6 md:pl-0 border-t md:border-t-0 md:border-l border-gray-100 md:justify-end">
                  {/* Editar - Primario */}
                  <button
                    onClick={() => { setEditingUser(user); setShowModal(true) }}
                    className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 active:bg-indigo-800 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
                  >
                    <Edit size={16} />
                    <span>Editar</span>
                  </button>

                  {/* Desactivar/Activar - Secundario outline */}
                  <button
                    onClick={() => handleToggleStatus(user.id, user.is_active)}
                    className={`flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium border transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                      user.is_active
                        ? 'border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-gray-500'
                        : 'border-emerald-300 text-emerald-700 hover:bg-emerald-50 focus:ring-emerald-500'
                    }`}
                  >
                    <Power size={16} />
                    <span className="hidden sm:inline">{user.is_active ? 'Desactivar' : 'Activar'}</span>
                    <span className="sm:hidden">{user.is_active ? 'Off' : 'On'}</span>
                  </button>

                  {/* Eliminar - Texto discreto */}
                  <button
                    onClick={() => handleDelete(user.id)}
                    className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                    aria-label="Eliminar hermano(a)"
                  >
                    <Trash size={16} />
                    <span className="hidden sm:inline">Eliminar</span>
                    <span className="sm:hidden">×</span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <UserModal
          user={editingUser}
          onClose={() => { setShowModal(false); setEditingUser(null) }}
          onSave={handleSave}
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

function UserModal({ user, onClose, onSave }) {
  const [formData, setFormData] = useState({
    nombre: user?.nombre || '',
    congregacion: user?.congregacion || '',
    telefono: user?.telefono || '',
    genero: user?.genero || 'hermano',
    is_active: user?.is_active ?? true
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-2 sm:p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-xl max-w-lg w-full p-6 sm:p-8 my-4 sm:my-8 max-h-[95vh] overflow-y-auto shadow-xl">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
              <Users className="text-white" size={20} />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">
              {user ? 'Editar Hermano(a)' : 'Nuevo Hermano(a)'}
            </h2>
          </div>
          <p className="text-sm text-gray-500 ml-13">
            {user ? 'Actualiza la información del hermano(a)' : 'Completa los datos para registrar un nuevo hermano(a)'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Nombre */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Nombre Completo *
            </label>
            <input
              type="text"
              value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              className="input w-full"
              placeholder="Ej: Juan Pérez"
              required
            />
          </div>

          {/* Teléfono y Género en fila */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Teléfono *
              </label>
              <input
                type="tel"
                value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                className="input w-full"
                placeholder="3101234567"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Género *
              </label>
              <select
                value={formData.genero}
                onChange={(e) => setFormData({ ...formData, genero: e.target.value })}
                className="input w-full"
                required
              >
                <option value="hermano">Hermano</option>
                <option value="hermana">Hermana</option>
              </select>
            </div>
          </div>

          {/* Congregación */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Congregación <span className="text-gray-400 font-normal">(Opcional)</span>
            </label>
            <input
              type="text"
              value={formData.congregacion}
              onChange={(e) => setFormData({ ...formData, congregacion: e.target.value })}
              className="input w-full"
              placeholder="Ej: SUR, PORVENIR, etc."
            />
          </div>

          {/* Estado activo */}
          <div className="bg-gray-50 rounded-lg p-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="w-5 h-5 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
              />
              <div>
                <span className="text-sm font-semibold text-gray-700">Hermano(a) Activo</span>
                <p className="text-xs text-gray-500 mt-0.5">
                  Los hermanos inactivos no podrán solicitar turnos
                </p>
              </div>
            </label>
          </div>

          {/* Botones */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-gray-200">
            <button
              type="submit"
              className="btn btn-primary flex-1 py-3 text-base font-semibold"
            >
              {user ? 'Guardar Cambios' : 'Crear Hermano(a)'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary flex-1 py-3 text-base"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
