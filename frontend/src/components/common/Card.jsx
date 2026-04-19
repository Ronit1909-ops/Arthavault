import React from 'react'

export default function Card({ children, className = '', glass = false, ...props }) {
  return (
    <div className={`${glass ? 'card-glass' : 'card'} p-5 ${className}`} {...props}>
      {children}
    </div>
  )
}
