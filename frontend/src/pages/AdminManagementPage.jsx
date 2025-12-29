import { useState, useEffect } from 'react'
import logger from '../utils/logger'
import { useNavigate } from 'react-router-dom'
import { Shield, UserPlus, Edit, Trash, ArrowLeft, Power } from 'lucide-react'
import client from '../api/client'
import ConfirmationModal from '../components/ConfirmationModal'

export default function AdminManagementPage() {
  const [admins, setAdmins] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingAdmin, setEditingAdmin] = useState(null)
  const [confirmationModal, setConfirmationModal] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [adminsRes, hermanosRes] = await Promise.all([
        client.get('/admin/admins'),
        client.get('/admin/hermanos')
      ])
      setAdmins(adminsRes.data)
      setUsers(hermanosRes.data)
    } catch (error) {
      logger.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (adminData) => {
    try {
      if (editingAdmin) {
        await client.patch(`/admin/admins/${editingAdmin.id}`, adminData)
      } else {
        await client.post('/admin/admins', adminData)
      }
      setShowModal(false)
      setEditingAdmin(null)
      loadData()
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleToggleAdminStatus = async (admin) => {
    try {
      // Toggle the hermano or user status
      if (admin.hermano_id) {
        await client.patch(`/admin/hermanos/${admin.hermano_id}`, {
          is_active: !admin.hermano.is_active
        })
      } else if (admin.user_id) {
        await client.patch(`/admin/users/${admin.user_id}`, {
          is_active: !admin.user.is_active
        })
      }
      loadData()
    } catch (error) {
      alert('Error: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleDelete = async (adminId) => {
    setConfirmationModal({
      isOpen: true,
      title: '¿Eliminar Administrador?',
      message: '¿Está seguro de eliminar este administrador?',
      confirmText: 'Sí, Eliminar',
      cancelText: 'Cancelar',
      onConfirm: async () => {
        setConfirmationModal(null)
        try {
          await client.delete(`/admin/admins/${adminId}`)
          loadData()
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
              Gestión de Administradores
            </h1>
            <p className="text-gray-600">
              {admins.length} administradores activos
            </p>
          </div>
          <button
            onClick={() => { setEditingAdmin(null); setShowModal(true) }}
            className="btn btn-primary flex items-center gap-2 w-full md:w-auto"
          >
            <UserPlus size={20} />
            Nuevo Admin
          </button>
        </div>
      </header>

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {admins.map((admin) => (
            <div
              key={admin.id}
              className="card border border-gray-200 bg-white/80 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Layout principal: info izquierda, acciones derecha */}
              <div className="flex flex-col lg:flex-row lg:items-stretch gap-6 lg:gap-8">
                {/* Columna izquierda: identidad + contacto + información */}
                <div className="flex-1 flex gap-4">
                  {/* Avatar / Icono */}
                  <div className="relative flex-shrink-0">
                    <div className={`h-12 w-12 rounded-full flex items-center justify-center shadow-md ${
                      admin.role === 'super_admin'
                        ? 'bg-gradient-to-br from-purple-500 to-purple-700'
                        : 'bg-gradient-to-br from-blue-500 to-blue-700'
                    }`}>
                      <Shield className="text-white" size={22} />
                    </div>
                    {/* Estado activo/inactivo */}
                    <span
                      className={`mt-2 inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        (admin.hermano?.is_active ?? admin.user?.is_active)
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          (admin.hermano?.is_active ?? admin.user?.is_active) ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      />
                      {(admin.hermano?.is_active ?? admin.user?.is_active) ? 'Activo' : 'Inactivo'}
                    </span>
                  </div>

                  {/* Contenido textual */}
                  <div className="flex-1 space-y-3">
                    {/* Encabezado: nombre + badges */}
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">
                          {admin.hermano ? admin.hermano.nombre : admin.user?.full_name}
                        </h3>
                        <p className="text-sm text-gray-600 font-mono">
                          Usuario: {admin.username}
                        </p>
                      </div>

                      {/* Badge de rol */}
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide self-start ${
                          admin.role === 'super_admin'
                            ? 'bg-purple-50 text-purple-700 border border-purple-200'
                            : 'bg-blue-50 text-blue-700 border border-blue-200'
                        }`}
                      >
                        {admin.role === 'super_admin' ? 'Super Administrador' : 'Líder de Exhibidor'}
                      </span>
                    </div>

                    {/* Sección contacto */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-50 rounded-lg p-3">
                      {/* Teléfono/Email */}
                      <div className="space-y-1">
                        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                          Contacto
                        </p>
                        <div className="text-sm text-gray-700">
                          <span className="font-mono">
                            {admin.hermano ? admin.hermano.telefono : admin.user?.phone}
                          </span>
                        </div>
                        {admin.user?.email && (
                          <div className="text-xs text-gray-600">{admin.user.email}</div>
                        )}
                      </div>

                      {/* Congregación */}
                      {admin.hermano?.congregacion && (
                        <div className="space-y-1">
                          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                            Congregación
                          </p>
                          <div className="text-sm text-gray-700">
                            {admin.hermano.congregacion}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Exhibidores asignados */}
                    {admin.exhibitor_roles && admin.exhibitor_roles.length > 0 && (
                      <div className="bg-blue-50 rounded-lg p-3">
                        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide mb-2">
                          Exhibidores asignados
                        </p>
                        <div className="space-y-1">
                          {admin.exhibitor_roles.map((er, idx) => (
                            <div key={idx} className="text-sm text-gray-700">
                              <span className="font-medium">{er.exhibitor_name}</span>
                              <span className="text-gray-600 ml-1">({er.position})</span>
                            </div>
                          ))}
                        </div>
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
                      onClick={() => { setEditingAdmin(admin); setShowModal(true) }}
                      className="btn btn-primary flex-1 justify-center py-2.5 text-sm font-semibold"
                    >
                      <Edit size={18} className="mr-2" />
                      Editar perfil
                    </button>

                    {/* Activar/Desactivar - warning outline */}
                    <button
                      onClick={() => handleToggleAdminStatus(admin)}
                      className={`flex-1 inline-flex items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                        (admin.hermano?.is_active ?? admin.user?.is_active)
                          ? 'border-orange-500 text-orange-600 hover:bg-orange-50'
                          : 'border-green-500 text-green-600 hover:bg-green-50'
                      }`}
                    >
                      <Power size={18} />
                      {(admin.hermano?.is_active ?? admin.user?.is_active) ? 'Desactivar' : 'Activar'}
                    </button>

                    {/* Eliminar - danger ghost */}
                    <button
                      onClick={() => handleDelete(admin.id)}
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

      {showModal && (
        <AdminModal
          admin={editingAdmin}
          users={users}
          onClose={() => { setShowModal(false); setEditingAdmin(null) }}
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

function AdminModal({ admin, users, onClose, onSave }) {
  const [formData, setFormData] = useState({
    user_id: admin?.user_id || '',
    hermano_id: admin?.hermano_id || '',
    username: admin?.username || '',
    password: '',
    role: admin?.role || 'lider_exhibidor'
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-2 sm:p-4 z-50 overflow-y-auto">
      <div className="bg-white rounded-xl max-w-md w-full p-4 sm:p-6 my-4 sm:my-8 max-h-[95vh] overflow-y-auto">
        <h2 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6">
          {admin ? 'Editar Administrador' : 'Nuevo Administrador'}
        </h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 font-medium mb-2">
              Hermano
            </label>
            <select
              value={formData.hermano_id || formData.user_id || ''}
              onChange={(e) => {
                if (e.target.value) {
                  // Check if it's a hermano (from users list which is actually hermanos)
                  const selected = users.find(u => u.id === e.target.value)
                  if (selected) {
                    setFormData({ ...formData, hermano_id: e.target.value, user_id: '' })
                  } else {
                    setFormData({ ...formData, user_id: e.target.value, hermano_id: '' })
                  }
                } else {
                  setFormData({ ...formData, hermano_id: '', user_id: '' })
                }
              }}
              className="input"
              required={!admin}
              disabled={!!admin}
            >
              <option value="">Seleccionar hermano...</option>
              {users.map(hermano => (
                <option key={hermano.id} value={hermano.id}>
                  {hermano.nombre} ({hermano.telefono}){hermano.congregacion ? ` - ${hermano.congregacion}` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="mb-4">
            <label className="block text-gray-700 font-medium mb-2">
              Nombre de Usuario
            </label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="input"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-gray-700 font-medium mb-2">
              Contraseña {admin && '(dejar vacío para no cambiar)'}
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="input"
              required={!admin}
            />
          </div>

          <div className="mb-6">
            <label className="block text-gray-700 font-medium mb-2">
              Perfil de administrador
            </label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="input"
              required
            >
              <option value="super_admin">Super Administrador (toda la plataforma)</option>
              <option value="lider_exhibidor">Líder de Exhibidor (solo exhibidores asignados)</option>
            </select>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button type="submit" className="btn btn-primary flex-1 py-3 text-base">
              Guardar
            </button>
            <button type="button" onClick={onClose} className="btn btn-secondary flex-1 py-3 text-base">
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
