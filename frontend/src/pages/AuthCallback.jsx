import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore.js'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import toast from 'react-hot-toast'

/**
 * After Google OAuth, the backend sets an HttpOnly cookie and redirects to
 * /auth/me. The backend callback actually redirects to /auth/me which returns
 * JSON. For SPA flow we handle the redirect here: just call checkAuth().
 */
export default function AuthCallback() {
  const { checkAuth } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    checkAuth().then(() => {
      const { isAuthenticated } = useAuthStore.getState()
      if (isAuthenticated) {
        toast.success('Welcome back!')
        navigate('/dashboard', { replace: true })
      } else {
        toast.error('Authentication failed. Please try again.')
        navigate('/login', { replace: true })
      }
    })
  }, []) // eslint-disable-line

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-gray-50">
      <LoadingSpinner size="lg" />
      <p className="text-gray-600 text-sm">Completing sign-in…</p>
    </div>
  )
}
