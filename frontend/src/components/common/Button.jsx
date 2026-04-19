import React from 'react'
import LoadingSpinner from './LoadingSpinner.jsx'

/**
 * Button component
 * @param {string}   variant  - 'primary' | 'secondary' | 'danger'
 * @param {boolean}  loading  - shows spinner and disables
 * @param {boolean}  disabled
 */
export default function Button({
  children,
  variant = 'primary',
  loading = false,
  disabled = false,
  className = '',
  type = 'button',
  ...props
}) {
  const base = variant === 'danger'
    ? 'btn-danger'
    : variant === 'secondary'
    ? 'btn-secondary'
    : 'btn-primary'

  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={`${base} ${className}`}
      {...props}
    >
      {loading && <LoadingSpinner size="sm" className="text-current" />}
      {children}
    </button>
  )
}
