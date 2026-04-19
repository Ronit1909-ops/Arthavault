import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
        <AlertCircle className="w-6 h-6 text-red-500" />
      </div>
      <p className="text-sm text-gray-600 max-w-xs">{message || 'Something went wrong.'}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          <RefreshCw className="w-4 h-4" /> Try again
        </button>
      )}
    </div>
  )
}
