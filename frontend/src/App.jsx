import React, { Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore.js'
import LoadingSpinner from './components/common/LoadingSpinner.jsx'

// Lazy-loaded pages
const Login        = React.lazy(() => import('./pages/Login.jsx'))
const AuthCallback = React.lazy(() => import('./pages/AuthCallback.jsx'))
const Dashboard    = React.lazy(() => import('./pages/Dashboard.jsx'))
const Transactions = React.lazy(() => import('./pages/Transactions.jsx'))
const Upload       = React.lazy(() => import('./pages/Upload.jsx'))
const Insights     = React.lazy(() => import('./pages/Insights.jsx'))
const Layout       = React.lazy(() => import('./components/layout/Layout.jsx'))

/** Full-page spinner while lazy chunks load */
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <LoadingSpinner size="lg" />
    </div>
  )
}

/**
 * Guard: redirect unauthenticated users to /login.
 * Shows a spinner ONLY while the cookie auth check is in progress.
 */
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  if (isLoading) return <PageLoader />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

/**
 * Guard: redirect already-authenticated users away from /login.
 * Does NOT wait for isLoading — the Login page renders immediately,
 * then redirects to /dashboard once checkAuth() resolves.
 */
function PublicRoute({ children }) {
  const { isAuthenticated } = useAuthStore()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  const checkAuth = useAuthStore((s) => s.checkAuth)

  useEffect(() => {
    checkAuth()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public */}
          <Route path="/login"         element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/auth/callback" element={<AuthCallback />} />

          {/* Protected – wrapped in Layout (sidebar + navbar) */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index             element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"    element={<Dashboard />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="upload"       element={<Upload />} />
            <Route path="insights"     element={<Insights />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
