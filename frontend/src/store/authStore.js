import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      
      setAuth: (user, token) => {
        // Ensure is_admin is preserved
        const userData = user ? { ...user, is_admin: user.is_admin || false } : null
        set({ user: userData, token, isAuthenticated: true })
      },
      
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
    }
  )
)
