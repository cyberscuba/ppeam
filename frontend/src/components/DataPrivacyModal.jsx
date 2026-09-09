import { useState } from 'react'
import { X, CheckCircle } from 'lucide-react'

export default function DataPrivacyModal({ isOpen, onAccept, onReject }) {
  const [scrolledToBottom, setScrolledToBottom] = useState(false)

  const handleScroll = (e) => {
    const element = e.target
    const isAtBottom = element.scrollHeight - element.scrollTop <= element.clientHeight + 10
    setScrolledToBottom(isAtBottom)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="bg-primary-600 text-white p-4 sm:p-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <CheckCircle size={24} />
            <h2 className="text-lg sm:text-xl font-bold">Tratamiento de Datos Personales</h2>
          </div>
        </div>

        {/* Content */}
        <div
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 sm:p-6 text-sm sm:text-base text-gray-700"
        >
          <div className="space-y-4">
            <section>
              <h3 className="font-bold text-gray-900 mb-2">1. Información Recabada</h3>
              <p className="text-gray-600">
                En PPEAM recolectamos información personal incluyendo: nombre, número de teléfono,
                congregación y detalles sobre su participación en actividades de predicación.
              </p>
            </section>

            <section>
              <h3 className="font-bold text-gray-900 mb-2">2. Uso de la Información</h3>
              <p className="text-gray-600">
                Su información será utilizada únicamente para:
              </p>
              <ul className="list-disc list-inside text-gray-600 mt-2 space-y-1">
                <li>Gestionar su participación en exhibidores y franjas horarias</li>
                <li>Mantener registro de turnos y solicitudes</li>
                <li>Comunicaciones relacionadas con actividades</li>
                <li>Cumplimiento de objetivos administrativos</li>
              </ul>
            </section>

            <section>
              <h3 className="font-bold text-gray-900 mb-2">3. Protección de Datos</h3>
              <p className="text-gray-600">
                Sus datos están protegidos mediante encriptación y acceso restringido.
                Solo personal autorizado puede acceder a su información.
              </p>
            </section>

            <section>
              <h3 className="font-bold text-gray-900 mb-2">4. Derechos del Usuario</h3>
              <p className="text-gray-600">
                Usted tiene derecho a:
              </p>
              <ul className="list-disc list-inside text-gray-600 mt-2 space-y-1">
                <li>Acceder a sus datos personales</li>
                <li>Solicitar corrección de datos inexactos</li>
                <li>Solicitar eliminación de sus datos</li>
                <li>Conocer cómo se utilizan sus datos</li>
              </ul>
            </section>

            <section>
              <h3 className="font-bold text-gray-900 mb-2">5. Retención de Datos</h3>
              <p className="text-gray-600">
                Los datos se mantienen durante el tiempo que participe en el programa.
                Una vez finalizada su participación, los datos se conservan según los
                requisitos legales aplicables.
              </p>
            </section>

            <section>
              <h3 className="font-bold text-gray-900 mb-2">6. Contacto</h3>
              <p className="text-gray-600">
                Para consultas sobre tratamiento de datos, contacte al administrador del sistema.
              </p>
            </section>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4 sm:p-6 flex gap-3 justify-end flex-shrink-0 bg-gray-50">
          <button
            onClick={onReject}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 transition"
          >
            Rechazar
          </button>
          <button
            onClick={onAccept}
            disabled={!scrolledToBottom}
            className={`px-6 py-2 rounded-lg text-white font-medium transition ${
              scrolledToBottom
                ? 'bg-primary-600 hover:bg-primary-700'
                : 'bg-gray-400 cursor-not-allowed'
            }`}
          >
            {scrolledToBottom ? 'Aceptar' : 'Desplázate para aceptar'}
          </button>
        </div>
      </div>
    </div>
  )
}
