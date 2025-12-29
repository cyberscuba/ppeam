import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import client from '../api/client'
import logoPPEAM from '../images/LogoPPEAM.png'

export default function LoginPage() {
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [step, setStep] = useState('phone')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  const requestOTP = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await client.post('/auth/otp/request', { phone })
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
      const { data } = await client.post('/auth/otp/verify', { phone, code: otp })
      setAuth(data.user, data.access_token)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Código inválido')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full">
        <div className="card">
          <div className="flex flex-col items-center mb-8">
            <img 
              src={logoPPEAM} 
              alt="PPEAM Logo" 
              className="h-16 w-auto object-contain mb-4"
            />
            <h1 className="text-3xl font-bold text-center">Iniciar Sesión</h1>
            <p className="text-sm text-gray-600 mt-2 text-center">PPEAM Pereira</p>
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-200 text-red-800 px-4 py-3 rounded-lg mb-4">
              {error}
            </div>
          )}

          {step === 'phone' ? (
            <form onSubmit={requestOTP}>
              <div className="mb-6">
                <label className="block text-gray-700 font-medium mb-2 text-base">
                  Número de teléfono
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="input"
                  required
                  placeholder="+573001234567"
                />
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
                Código enviado a {phone}
              </p>

              <div className="mb-6">
                <label className="block text-gray-700 font-medium mb-2 text-base">
                  Código de verificación
                </label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  className="input text-center text-2xl"
                  required
                  maxLength={6}
                  placeholder="000000"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary w-full"
              >
                {loading ? 'Verificando...' : 'Verificar'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
