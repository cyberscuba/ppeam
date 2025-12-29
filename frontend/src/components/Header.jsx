import { useNavigate } from 'react-router-dom'
import { Home, LogOut, Shield } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import logoPPEAM from '../images/LogoPPEAM.png'

export default function Header({ showAdmin = false }) {
  const navigate = useNavigate()
  const { isAuthenticated, user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="header-app sticky top-0 z-50">
      <div className="container mx-auto max-w-7xl">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-3 hover:opacity-80 transition-opacity"
            >
              <img 
                src={logoPPEAM} 
                alt="PPEAM Logo" 
                className="h-12 w-auto object-contain"
              />
              <div className="hidden sm:block">
                <h1 className="font-bold text-lg leading-tight text-gray-600">PPEAM Pereira</h1>
                <p className="text-xs text-gray-500">Predicación Pública Especial  Áreas Metropolitanas</p>
              </div>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Botón Volver al Inicio - siempre visible */}
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-600"
              title="Volver al Inicio"
            >
              <Home size={20} className="text-gray-600" />
              <span className="hidden sm:inline text-gray-600">Inicio</span>
            </button>
            
            {/* Link a administración - siempre visible */}
            {isAuthenticated && user?.is_admin ? (
              <button
                onClick={() => navigate('/admin')}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-600"
                title="Panel de Administración"
              >
                <Shield size={20} className="text-gray-600" />
                <span className="hidden sm:inline text-gray-600">Admin</span>
              </button>
            ) : (
              <button
                onClick={() => navigate('/admin/login')}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors text-sm text-gray-600"
                title="Acceso Administración"
              >
                <Shield size={18} className="text-gray-600" />
                <span className="hidden sm:inline text-gray-600">Admin</span>
              </button>
            )}
            
            {isAuthenticated && (
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-600"
                title="Cerrar Sesión"
              >
                <LogOut size={20} className="text-gray-600" />
                <span className="hidden sm:inline text-gray-600">Salir</span>
              </button>
            )}
          </div>
        </div>
        
        {/* Texto inspiracional */}
        <div className="mt-3 pt-3 border-t border-gray-300">
          <p className="text-sm text-center text-gray-600 italic">
            "¿Dirá usted: '¡Aquí estoy yo! Envíame a mí'?"{' '}
            <a 
              href="https://www.jw.org/es/biblioteca/biblia/biblia-estudio/libros/Isa%C3%ADas/6/#v23006008"
              target="_blank"
              rel="noopener noreferrer"
              className="not-italic font-semibold underline text-gray-700 hover:text-gray-900 transition-colors"
              title="Leer Isaías 6:8"
            >
              (Isaías 6:8)
            </a>
          </p>
        </div>
      </div>
    </header>
  )
}
