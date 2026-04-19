import axios from 'axios'
import useAuthStore from '../store/authStore.js'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Axios instance.
 * - withCredentials: true  → sends HttpOnly cookie (access_token) on every request
 * - No Authorization header needed — backend reads the cookie
 */
const axiosInstance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,       // critical for cookie-based auth
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Response interceptor ──────────────────────────────────────────────────────
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status

    if (status === 401) {
      // Clear client-side auth state — the ProtectedRoute in App.jsx will
      // redirect to /login. We do NOT redirect here to avoid races with checkAuth().
      useAuthStore.getState().logout()
    }

    return Promise.reject(error)
  },
)

// ── API methods ───────────────────────────────────────────────────────────────
const api = {
  auth: {
    /** Redirects browser to Google OAuth — do not call via fetch */
    login: () => {
      window.location.href = `${BASE_URL}/auth/login`
    },

    /** Returns current authenticated user */
    me: async () => {
      const res = await axiosInstance.get('/auth/me')
      return res.data
    },

    logout: async () => {
      const res = await axiosInstance.post('/auth/logout')
      return res.data
    },
  },

  transactions: {
    /**
     * @param {Object} filters - { bank, type, date_from, date_to, page, page_size }
     */
    getAll: async (filters = {}) => {
      const params = {}
      if (filters.bank)       params.bank       = filters.bank
      if (filters.type)       params.type       = filters.type
      if (filters.date_from)  params.date_from  = filters.date_from
      if (filters.date_to)    params.date_to    = filters.date_to
      if (filters.page)       params.page       = filters.page
      if (filters.page_size)  params.page_size  = filters.page_size

      const res = await axiosInstance.get('/statements/transactions', { params })
      return res.data // { page, page_size, total, data: [...] }
    },

    create: async (data) => {
      const res = await axiosInstance.post('/transactions', data)
      return res.data
    },

    update: async (id, data) => {
      const res = await axiosInstance.put(`/statements/transactions/${id}`, data)
      return res.data
    },

    delete: async (id) => {
      const res = await axiosInstance.delete(`/statements/transactions/${id}`)
      return res.data
    },
  },

  upload: {
    /** Upload a PDF bank statement — multipart/form-data */
    statement: async (file, password = null, bank = null, onProgress = null) => {
      const formData = new FormData()
      formData.append('file', file)
      if (password) formData.append('password', password)

      const params = {}
      if (bank) params.bank = bank

      const res = await axiosInstance.post('/statements/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        params,
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onProgress(pct)
          }
        },
      })
      return res.data
    },
  },

  ml: {
    forecast: async (userId, days = 30) => {
      const res = await axiosInstance.get(`/ml/forecast/${userId}`, { params: { days } })
      return res.data
    },

    anomalies: async (userId, days = 30) => {
      const res = await axiosInstance.get(`/ml/anomalies/${userId}`, { params: { days } })
      return res.data
    },

    categorize: async (merchant, amount, hour = 12, day_of_week = 0) => {
      const res = await axiosInstance.post('/ml/categorize', { merchant, amount, hour, day_of_week })
      return res.data
    },

    health: async () => {
      const res = await axiosInstance.get('/ml/health')
      return res.data
    },
  },
}

export default api
