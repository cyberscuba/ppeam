import { AlertTriangle, X } from 'lucide-react'

/**
 * Modal de confirmación personalizado
 * @param {boolean} isOpen - Si el modal está abierto
 * @param {string} title - Título del modal
 * @param {string} message - Mensaje principal
 * @param {string} confirmText - Texto del botón de confirmación (default: "Confirmar")
 * @param {string} cancelText - Texto del botón de cancelación (default: "Cancelar")
 * @param {function} onConfirm - Función a ejecutar al confirmar
 * @param {function} onCancel - Función a ejecutar al cancelar
 */
export default function ConfirmationModal({ 
  isOpen, 
  title, 
  message, 
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  onConfirm, 
  onCancel 
}) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full animate-slide-up">
        {/* Header con botón cerrar */}
        <div className="flex justify-end p-4 pb-0">
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Cerrar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Contenido */}
        <div className="px-6 pb-6 pt-2">
          {/* Icono */}
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-orange-100 mb-4">
            <AlertTriangle className="h-8 w-8 text-orange-600" />
          </div>

          {/* Título */}
          <h3 className="text-2xl font-bold text-center mb-3 text-gray-900">
            {title}
          </h3>

          {/* Mensaje principal */}
          <p className="text-gray-700 text-center text-base mb-6">
            {message}
          </p>

          {/* Botones de acción */}
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-3 px-6 rounded-xl transition-all hover:shadow-lg text-lg"
            >
              {cancelText}
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 bg-orange-600 hover:bg-orange-700 text-white font-bold py-3 px-6 rounded-xl transition-all hover:shadow-lg text-lg"
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

