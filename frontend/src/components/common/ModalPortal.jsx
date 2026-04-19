import React, { useEffect } from 'react'
import ReactDOM from 'react-dom'

/**
 * Renders children into document.body via a React Portal.
 * This ensures fixed/absolute positioning always works relative
 * to the true viewport, regardless of parent CSS (overflow, transform, etc.).
 */
export default function ModalPortal({ children, onClose }) {
  // Lock body scroll while modal is open
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [])

  // Close on Escape
  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose?.() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  return ReactDOM.createPortal(children, document.body)
}
