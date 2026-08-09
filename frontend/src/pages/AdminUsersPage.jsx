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
      const { data } = await client.get('/api/api/admin/hermanos')
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
        await client.post('/api/api/admin/hermanos', userData)
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
        <div className="grid grid-cols-1 gap-4">
          {filteredUsers.map((user) => (
            <div
              key={user.id}
              className="card border border-gray-200 bg-white/80 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Layout principal: info izquierda, acciones derecha */}
              <div className="flex flex-col lg:flex-row lg:items-stretch gap-6 lg:gap-8">
                {/* Columna izquierda: identidad + contacto + información */}
                <div className="flex-1 flex gap-4">
                  {/* Avatar / Icono */}
                  <div className="relative flex-shrink-0">
                    <div className="h-12 w-12 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-md">
                      <Users className="text-white" size={22} />
                    </div>
                    {/* Estado activo/inactivo */}
                    <span
                      className={`mt-2 inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        user.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          user.is_active ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      />
                      {user.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </div>

                  {/* Contenido textual */}
                  <div className="flex-1 space-y-3">
                    {/* Encabezado: nombre + badges */}
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">
                          {user.nombre}
                        </h3>
                      </div>

                      {/* Badges de rol */}
                      <div className="flex flex-wrap gap-2">
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${
                            user.gender_label === 'Hermana'
                              ? 'bg-pink-50 text-pink-700 border border-pink-200'
                              : 'bg-blue-50 text-blue-700 border border-blue-200'
                          }`}
                        >
                          {user.gender_label || 'Hermano'}
                        </span>
                        {user.is_admin && (
                          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide bg-purple-50 text-purple-700 border border-purple-200">
                            Administrador
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Sección contacto */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-50 rounded-lg p-3">
                      {/* Teléfono */}
                      <div className="space-y-1">
                        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                          Contacto
                        </p>
                        <div className="flex items-center text-sm text-gray-700 gap-2">
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-gray-100 text-gray-500">
                            <Phone size={14} />
                          </span>
                          <span className="font-mono">{user.telefono}</span>
                        </div>
                      </div>

                      {/* Congregación */}
                      {user.congregacion && (
                        <div className="space-y-1">
                          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                            Congregación
                          </p>
                          <div className="flex items-center text-sm text-gray-700 gap-2">
                            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-gray-100 text-gray-500">
                              <MapPin size={14} />
                            </span>
                            <span>{user.congregacion}</span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Sección metadatos */}
                    {user.created_at && (
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Calendar size={14} />
                        <span>
                          Registrado: {new Date(user.created_at).toLocaleDateString('es-ES', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Columna derecha: acciones */}
                <div className="w-full lg:w-1/3 flex flex-col justify-between gap-3">
                  {/* Botones de acción */}
                  <div className="flex flex-col sm:flex-row lg:flex-col gap-2">
                    {/* Editar - primario */}
                    <button
                      onClick={() => { setEditingUser(user); setShowModal(true) }}
                      className="btn btn-primary flex-1 justify-center py-2.5 text-sm font-semibold"
                    >
                      <Edit size={18} className="mr-2" />
                      Editar perfil
                    </button>

                    {/* Activar/Desactivar - warning outline */}
                    <button
                      onClick={() => handleToggleStatus(user.id, user.is_active)}
                      className={`flex-1 inline-flex items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                        user.is_active
                          ? 'border-orange-500 text-orange-600 hover:bg-orange-50'
                          : 'border-green-500 text-green-600 hover:bg-green-50'
                      }`}
                    >
                      <Power size={18} />
                      {user.is_active ? 'Desactivar' : 'Activar'}
                    </button>

                    {/* Eliminar - danger ghost */}
                    <button
                      onClick={() => handleDelete(user.id)}
                      className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg border border-transparent px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50"
                    >
                      <Trash size={18} />
                      Eliminar
                    </button>
                  </div>
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
