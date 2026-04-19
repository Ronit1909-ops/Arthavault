import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: { fontSize: '14px', fontFamily: 'Inter, sans-serif' },
        success: { iconTheme: { primary: '#16a34a', secondary: '#fff' } },
        error:   { iconTheme: { primary: '#dc2626', secondary: '#fff' } },
      }}
    />
  </React.StrictMode>,
)
