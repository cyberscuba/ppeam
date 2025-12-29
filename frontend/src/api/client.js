import axios from 'axios'
import { useAuthStore } from '../store/authStore'

// Use relative path for production (through nginx proxy) or env variable for development
// In production, nginx routes backend requests directly (no /api prefix needed)
const API_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8080')

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401/403 errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect on 401/403 if not already on login page and not during admin verification
    const currentPath = window.location.pathname
    const isLoginPage = currentPath.includes('/login')
    const isAdminVerification = error.config?.url?.includes('/admin/requests') && error.config?.params?.limit === '1'
    
    if ((error.response?.status === 401 || error.response?.status === 403) && 
        !isLoginPage && !isAdminVerification) {
      const errorDetail = error.response?.data?.detail || error.message
      
      // Check if it's a token expiration issue
      if (errorDetail.includes('token') || errorDetail.includes('credentials') || errorDetail.includes('Invalid')) {
        // Show a more user-friendly message
        if (currentPath.startsWith('/admin')) {
          alert('Su sesión ha expirado. Por favor, inicie sesión nuevamente.')
        } else {
          alert('Su sesión ha expirado. Por favor, inicie sesión nuevamente.')
        }
      }
      
      const { logout } = useAuthStore.getState()
      logout()
      
      // Redirect to appropriate login based on current path
      if (currentPath.startsWith('/admin')) {
        window.location.href = '/admin/login'
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default client
