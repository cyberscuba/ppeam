import { Routes, Route, useLocation } from 'react-router-dom'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import AdminLoginPage from './pages/AdminLoginPage'
import AdminPointsPage from './pages/AdminPointsPage'
import AdminReportsPage from './pages/AdminReportsPage'
import AdminUsersPage from './pages/AdminUsersPage'
import AdminManagementPage from './pages/AdminManagementPage'
import Header from './components/Header'
import AdminRoute from './components/AdminRoute'
import { useAuthStore } from './store/authStore'

function App() {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()
  
  // No mostrar header en páginas de login
  const hideHeader = location.pathname === '/admin/login' || location.pathname === '/login'

  return (
    <div className="min-h-screen">
      {!hideHeader && <Header />}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route path="/admin" element={<AdminRoute><AdminPage /></AdminRoute>} />
        <Route path="/admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
        <Route path="/admin/admins" element={<AdminRoute><AdminManagementPage /></AdminRoute>} />
        <Route path="/admin/points" element={<AdminRoute><AdminPointsPage /></AdminRoute>} />
        <Route path="/admin/reports" element={<AdminRoute><AdminReportsPage /></AdminRoute>} />
      </Routes>
    </div>
  )
}

export default App
