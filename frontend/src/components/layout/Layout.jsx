import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar.jsx'
import Navbar  from './Navbar.jsx'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-[#0f1117] overflow-hidden relative">
      {/* Ambient background orbs */}
      <div className="orb orb-violet w-[500px] h-[500px] -top-40 -left-20 opacity-[0.08]" />
      <div className="orb orb-blue   w-[400px] h-[400px] top-1/2 -right-32 opacity-[0.06]" />
      <div className="orb orb-pink   w-[300px] h-[300px] bottom-0 left-1/3 opacity-[0.05]" />

      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden relative z-10">
        <Navbar onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
