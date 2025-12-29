import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react'

/**
 * Modal de notificación personalizado
 * @param {string} type - 'success' | 'error' | 'warning' | 'info'
 * @param {string} title - Título del modal
 * @param {string} message - Mensaje principal
 * @param {array} details - Array de strings con detalles adicionales (opcional)
 * @param {function} onClose - Función para cerrar el modal
 */
export default function NotificationModal({ type = 'info', title, message, details = [], onClose }) {
  // Configuración según el tipo
  const config = {
    success: {
      icon: CheckCircle,
      bgGradient: 'from-green-50 to-emerald-50',
      borderColor: 'border-green-300',
      iconBgColor: 'bg-green-100',
      iconColor: 'text-green-600',
      titleColor: 'text-green-900',
      buttonColor: 'bg-green-600 hover:bg-green-700'
    },
    error: {
      icon: XCircle,
      bgGradient: 'from-red-50 to-pink-50',
      borderColor: 'border-red-300',
      iconBgColor: 'bg-red-100',
      iconColor: 'text-red-600',
      titleColor: 'text-red-900',
      buttonColor: 'bg-red-600 hover:bg-red-700'
    },
    warning: {
      icon: AlertCircle,
      bgGradient: 'from-yellow-50 to-orange-50',
      borderColor: 'border-yellow-300',
      iconBgColor: 'bg-yellow-100',
      iconColor: 'text-yellow-600',
      titleColor: 'text-yellow-900',
      buttonColor: 'bg-yellow-600 hover:bg-yellow-700'
    },
    info: {
      icon: AlertCircle,
      bgGradient: 'from-blue-50 to-cyan-50',
      borderColor: 'border-blue-300',
      iconBgColor: 'bg-blue-100',
      iconColor: 'text-blue-600',
      titleColor: 'text-blue-900',
      buttonColor: 'bg-blue-600 hover:bg-blue-700'
    }
  }

  const currentConfig = config[type] || config.info
  const IconComponent = currentConfig.icon

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full animate-slide-up">
        {/* Header con botón cerrar */}
        <div className="flex justify-end p-4 pb-0">
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Cerrar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Contenido */}
        <div className="px-6 pb-6 pt-2">
          {/* Icono */}
          <div className={`mx-auto flex items-center justify-center h-16 w-16 rounded-full ${currentConfig.iconBgColor} mb-4`}>
            <IconComponent className={`h-8 w-8 ${currentConfig.iconColor}`} />
          </div>

          {/* Título */}
          <h3 className={`text-2xl font-bold text-center mb-3 ${currentConfig.titleColor}`}>
            {title}
          </h3>

          {/* Mensaje principal */}
          <p className="text-gray-700 text-center text-base mb-4">
            {message}
          </p>

          {/* Detalles adicionales (si los hay) */}
          {details && details.length > 0 && (
            <div className={`bg-gradient-to-r ${currentConfig.bgGradient} border-2 ${currentConfig.borderColor} rounded-xl p-4 mb-4`}>
              <ul className="space-y-2">
                {details.map((detail, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className={`${currentConfig.iconColor} mt-0.5`}>•</span>
                    <span className="flex-1">{detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Botón de acción */}
          <button
            onClick={onClose}
            className={`w-full ${currentConfig.buttonColor} text-white font-bold py-3 px-6 rounded-xl transition-all hover:shadow-lg text-lg`}
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  )
}

