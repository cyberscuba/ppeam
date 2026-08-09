import { useState } from 'react'
import logger from '../utils/logger'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import client from '../api/client'
import { Lock, User } from 'lucide-react'
import logoPPEAM from '../images/LogoPPEAM.png'

export default function AdminLoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const { data } = await client.post('/api/auth/admin/login', {
        username,
        password
      })
      
      // Ensure is_admin is set
      const userData = {
        ...data.user,
        is_admin: true  // Always true for admin login
      }
      
      setAuth(userData, data.access_token)
      navigate('/admin')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión')
      logger.error('Admin login error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 px-4">
      <div className="max-w-md w-full">
        <div className="card">
          <div className="text-center mb-8">
            <img 
              src={logoPPEAM} 
              alt="PPEAM Logo" 
              className="h-20 w-auto object-contain mx-auto mb-4"
            />
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              PPEAM Pereira
            </h1>
            <p className="text-gray-600 text-base">
              Predicación Pública Especial Áreas Metropolitanas
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Panel de Administración
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-200 text-red-800 px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-gray-700 font-medium mb-2 text-base">
                Administrador
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input pl-12"
                  required
                  placeholder="admin"
                  autoFocus
                />
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-gray-700 font-medium mb-2 text-base">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pl-12"
                  required
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full mb-4"
            >
              {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
            </button>

            <button
              type="button"
              onClick={() => navigate('/')}
              className="btn btn-secondary w-full"
            >
              Volver al inicio
            </button>
          </form>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-gray-700 font-medium mb-2">
              Administradores por defecto:
            </p>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• <strong>admin</strong> / admin123</li>
              <li>• <strong>supervisor</strong> / super123</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
