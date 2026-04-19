import React, { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, List, Upload, TrendingUp, X, IndianRupee, ChevronRight,
} from 'lucide-react'

const links = [
  { to: '/dashboard',    label: 'Dashboard',    icon: LayoutDashboard, color: 'text-violet-400' },
  { to: '/transactions', label: 'Transactions', icon: List,            color: 'text-blue-400'   },
  { to: '/upload',       label: 'Upload',       icon: Upload,          color: 'text-emerald-400' },
  { to: '/insights',     label: 'Insights',     icon: TrendingUp,      color: 'text-orange-400' },
]

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed z-30 top-0 left-0 h-full w-64
          bg-[#0d0f1a]/95 border-r border-white/[0.06]
          backdrop-blur-2xl flex flex-col
          transition-transform duration-300 ease-out
          lg:translate-x-0 lg:static lg:shadow-none
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
        aria-label="Sidebar navigation"
      >
        {/* Ambient glow */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-40 h-40 rounded-full
                        bg-violet-600/20 blur-3xl pointer-events-none" />

        {/* Logo */}
        <div className="flex items-center justify-between px-5 h-16 border-b border-white/[0.06] relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600
                           flex items-center justify-center shadow-[0_0_16px_rgba(109,40,217,0.5)]">
              <IndianRupee className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="font-bold text-white text-sm tracking-tight">UPI Tracker</span>
              <p className="text-[10px] text-gray-500 leading-none mt-0.5">Finance Dashboard</p>
            </div>
          </div>
          <button onClick={onClose} className="lg:hidden text-gray-500 hover:text-gray-300 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-5 space-y-1 relative z-10" role="navigation">
          <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest px-3 mb-3">Menu</p>
          {links.map(({ to, label, icon: Icon, color }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `group flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium
                 transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-violet-600/25 to-indigo-600/10 text-white border border-violet-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/[0.05] border border-transparent'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all
                      ${isActive ? 'bg-violet-600/30' : 'bg-white/[0.04] group-hover:bg-white/[0.08]'}`}>
                      <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-violet-300' : color}`} />
                    </div>
                    {label}
                  </div>
                  {isActive && <ChevronRight className="w-3.5 h-3.5 text-violet-400" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-white/[0.06] relative z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)] animate-pulse-slow" />
            <p className="text-xs text-gray-500">v1.0 · All systems online</p>
          </div>
        </div>
      </aside>
    </>
  )
}
