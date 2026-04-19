import React, { useState, useRef, useEffect } from 'react'
import { Menu, LogOut, ChevronDown, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import useAuthStore from '../../store/authStore.js'
import api from '../../services/api.js'
import NotificationDropdown from '../common/NotificationDropdown.jsx'

export default function Navbar({ onMenuClick }) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropRef = useRef(null)

  useEffect(() => {
    function handler(e) {
      if (dropRef.current && !dropRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = async () => {
    try { await api.auth.logout() } catch {}
    logout()
    toast.success('Logged out successfully')
    navigate('/login')
  }

  return (
    <header className="h-16 bg-[#0d0f1a]/80 border-b border-white/[0.06] backdrop-blur-xl
                       flex items-center justify-between px-4 lg:px-6 flex-shrink-0 relative z-10">
      {/* Left: hamburger (mobile) */}
      <button
        onClick={onMenuClick}
        className="lg:hidden text-gray-400 hover:text-white p-2 rounded-lg
                   hover:bg-white/[0.06] transition-colors"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Centre — empty on desktop */}
      <div className="hidden lg:block" />

      {/* Right: actions */}
      <div className="flex items-center gap-2">
        {/* Smart notifications */}
        <NotificationDropdown />

        {/* User dropdown */}
        <div className="relative" ref={dropRef}>
          <button
            onClick={() => setDropdownOpen((o) => !o)}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl
                       hover:bg-white/[0.06] border border-transparent
                       hover:border-white/[0.08] transition-all duration-200"
          >
            {user?.picture ? (
              <img src={user.picture} alt={user.name}
                   className="w-8 h-8 rounded-full object-cover ring-2 ring-violet-500/40" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-600 to-indigo-600
                              flex items-center justify-center ring-2 ring-violet-500/40">
                <User className="w-4 h-4 text-white" />
              </div>
            )}
            <div className="hidden sm:block text-left">
              <p className="text-sm font-medium text-gray-200 leading-tight">{user?.name || 'User'}</p>
              <p className="text-[11px] text-gray-500 truncate max-w-[140px]">{user?.email}</p>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-gray-500 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-52 rounded-2xl border border-white/[0.08]
                            bg-[#13152a]/95 backdrop-blur-xl shadow-[0_16px_48px_rgba(0,0,0,0.6)]
                            py-1.5 z-50 animate-fade-in overflow-hidden">
              <div className="px-4 py-3 border-b border-white/[0.06]">
                <p className="text-sm font-semibold text-white truncate">{user?.name}</p>
                <p className="text-xs text-gray-500 truncate mt-0.5">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm
                           text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
              >
                <LogOut className="w-4 h-4" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
