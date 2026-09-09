import { CheckCircle } from 'lucide-react'

export default function DataPrivacyModal({ isOpen, onAccept, onReject }) {
  console.log('🔐 DataPrivacyModal render:', { isOpen })

  if (!isOpen) {
    console.log('📌 Modal not open, returning null')
    return null
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" style={{ display: 'flex' }}>
      <div className="bg-white rounded-lg shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-blue-600 text-white p-6 flex items-center gap-3 flex-shrink-0">
          <CheckCircle size={28} />
          <h2 className="text-2xl font-bold">Tratamiento de Datos Personales</h2>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 text-gray-700 space-y-4">
          <section>
            <h3 className="font-bold text-lg text-gray-900 mb-2">1. Información Recabada</h3>
            <p className="text-gray-600">
              En PPEAM recolectamos información personal incluyendo: nombre, número de teléfono,
              congregación y detalles sobre su participación en actividades de predicación.
            </p>
          </section>

          <section>
            <h3 className="font-bold text-lg text-gray-900 mb-2">2. Uso de la Información</h3>
            <p className="text-gray-600 mb-2">Su información será utilizada únicamente para:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-1">
              <li>Gestionar su participación en exhibidores y franjas horarias</li>
              <li>Mantener registro de turnos y solicitudes</li>
              <li>Comunicaciones relacionadas con actividades</li>
              <li>Cumplimiento de objetivos administrativos</li>
            </ul>
          </section>

          <section>
            <h3 className="font-bold text-lg text-gray-900 mb-2">3. Protección de Datos</h3>
            <p className="text-gray-600">
              Sus datos están protegidos mediante encriptación y acceso restringido.
              Solo personal autorizado puede acceder a su información.
            </p>
          </section>

          <section>
            <h3 className="font-bold text-lg text-gray-900 mb-2">4. Derechos del Usuario</h3>
            <p className="text-gray-600 mb-2">Usted tiene derecho a:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-1">
              <li>Acceder a sus datos personales</li>
              <li>Solicitar corrección de datos inexactos</li>
              <li>Solicitar eliminación de sus datos</li>
              <li>Conocer cómo se utilizan sus datos</li>
            </ul>
          </section>

          <section>
            <h3 className="font-bold text-lg text-gray-900 mb-2">5. Retención de Datos</h3>
            <p className="text-gray-600">
              Los datos se mantienen durante el tiempo que participe en el programa.
              Una vez finalizada su participación, los datos se conservan según los
              requisitos legales aplicables.
            </p>
          </section>

          <section>
            <h3 className="font-bold text-lg text-gray-900 mb-2">6. Contacto</h3>
            <p className="text-gray-600">
              Para consultas sobre tratamiento de datos, contacte al administrador del sistema.
            </p>
          </section>

          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
            <p className="text-blue-900 font-semibold">
              ✓ He leído y entiendo los términos de tratamiento de datos
            </p>
          </div>
        </div>

        {/* Footer - Botones */}
        <div className="border-t border-gray-200 p-6 flex gap-3 justify-end flex-shrink-0 bg-gray-50">
          <button
            onClick={() => {
              console.log('❌ Privacy rejected')
              onReject()
            }}
            className="px-6 py-3 border border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-100 transition"
          >
            Rechazar
          </button>
          <button
            onClick={() => {
              console.log('✅ Privacy accepted')
              onAccept()
            }}
            className="px-6 py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition"
          >
            Aceptar y Continuar
          </button>
        </div>
      </div>
    </div>
  )
}
