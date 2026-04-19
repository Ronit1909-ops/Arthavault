import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Auth store — persists user info to localStorage.
 * The actual session is managed as an HttpOnly cookie on the backend.
 *
 * isLoading starts as FALSE so the Login page renders immediately.
 * It is set to TRUE only during checkAuth(), and back to FALSE when done.
 */
const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,   // ← false by default: don't block render before checkAuth fires

      setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),

      logout: () => set({ user: null, isAuthenticated: false, isLoading: false }),

      setLoading: (isLoading) => set({ isLoading }),

      checkAuth: async () => {
        set({ isLoading: true })
        try {
          const { default: api } = await import('../services/api.js')
          const user = await api.auth.me()
          set({ user, isAuthenticated: true, isLoading: false })
        } catch {
          set({ user: null, isAuthenticated: false, isLoading: false })
        }
      },
    }),
    {
      name: 'upi-auth',
      // Persist only non-sensitive user metadata, never loading flag
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
)

export default useAuthStore
