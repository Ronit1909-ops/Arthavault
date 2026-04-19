import React from 'react'
import { Loader2 } from 'lucide-react'

const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-10 h-10' }

export default function LoadingSpinner({ size = 'md', className = '' }) {
  return (
    <Loader2
      className={`animate-spin text-blue-600 ${sizes[size] ?? sizes.md} ${className}`}
      aria-label="Loading"
    />
  )
}
