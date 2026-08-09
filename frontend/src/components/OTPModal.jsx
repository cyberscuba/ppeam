import { useState } from 'react'
import { X } from 'lucide-react'
import client from '../api/client'
import { useAuthStore } from '../store/authStore'

export default function OTPModal({ onClose, onSuccess }) {
  const [step, setStep] = useState('phone') // phone, otp
  const [phone, setPhone] = useState('')
  const [fullName, setFullName] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { setAuth } = useAuthStore()

  const requestOTP = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await client.post('/api/api/auth/otp/request', {
        phone,
        full_name: fullName
      })
      setStep('otp')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al enviar código')
    } finally {
      setLoading(false)
    }
  }

  const verifyOTP = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const { data } = await client.post('/api/api/auth/otp/verify', {
        phone,
        code: otp
      })
      setAuth(data.user, data.access_token)
      onClose()
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.detail || 'Código inválido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-md w-full p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          aria-label="Cerrar"
        >
          <X size={24} />
        </button>

        <h2 className="text-2xl font-bold mb-6">Verificación</h2>

        {error && (
          <div className="bg-red-50 border-2 border-red-200 text-red-800 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        {step === 'phone' ? (
          <form onSubmit={requestOTP}>
            <div className="mb-4">
              <label className="block text-gray-700 font-medium mb-2 text-base">
                Nombre completo
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="input"
                required
                placeholder="Juan Pérez"
              />
            </div>

            <div className="mb-6">
              <label className="block text-gray-700 font-medium mb-2 text-base">
                Teléfono
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="input"
                required
                placeholder="+573001234567"
              />
              <p className="text-sm text-gray-500 mt-1">
                Formato: +57 seguido de su número
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary w-full"
            >
              {loading ? 'Enviando...' : 'Enviar código'}
            </button>
          </form>
        ) : (
          <form onSubmit={verifyOTP}>
            <p className="text-gray-600 mb-4 text-base">
              Ingrese el código de 6 dígitos enviado a {phone}
            </p>

            <div className="mb-6">
              <label className="block text-gray-700 font-medium mb-2 text-base">
                Código OTP
              </label>
              <input
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="input text-center text-2xl tracking-widest"
                required
                maxLength={6}
                placeholder="000000"
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={loading || otp.length !== 6}
              className="btn btn-primary w-full mb-3"
            >
              {loading ? 'Verificando...' : 'Verificar'}
            </button>

            <button
              type="button"
              onClick={() => setStep('phone')}
              className="btn btn-secondary w-full"
            >
              Cambiar número
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
