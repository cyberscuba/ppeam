import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import client from '../api/client'
import logger from '../utils/logger'

export default function AdminRoute({ children }) {
  const navigate = useNavigate()
  const { isAuthenticated, user, token } = useAuthStore()
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const checkAdmin = async () => {
      if (!isAuthenticated || !token) {
        navigate('/api/admin/login')
        return
      }
      
      // Verify user is admin from token or user object
      if (user?.is_admin === true) {
        setChecking(false)
        return
      }
      
      // Try to verify admin access by making a test request
      try {
        // Use a lightweight endpoint to verify admin access (just get pending requests)
        await client.get('/api/api/admin/requests', {
          params: { status: 'pending' }
        })
        // If successful, update user to mark as admin
        if (!user?.is_admin) {
          useAuthStore.getState().setAuth({ ...user, is_admin: true }, token)
        }
        setChecking(false)
      } catch (error) {
        logger.error('Admin verification error:', error)
        // Only redirect if it's a clear 403, not network errors or 404
        if (error.response?.status === 403) {
          useAuthStore.getState().logout()
          alert('Acceso denegado. Se requieren permisos de administrador.')
          navigate('/api/admin/login')
        } else if (error.response?.status === 401) {
          // Token expired or invalid
          useAuthStore.getState().logout()
          navigate('/api/admin/login')
        } else {
          // For other errors (network, 404, etc), still allow access
          // The actual endpoints will handle the errors
          setChecking(false)
        }
      }
    }
    
    checkAdmin()
  }, [isAuthenticated, user, token, navigate])

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-primary-600 border-t-transparent"></div>
          <p className="mt-4 text-gray-600">Verificando acceso...</p>
        </div>
      </div>
    )
  }

  return children
}

