/**
 * NotificationDropdown.jsx
 *
 * Smart notification centre in the Navbar.
 * Sources:
 *   1. ML anomaly alerts (last 30 days)
 *   2. Budget overages — current-month spend vs limit
 *   3. Upload confirmations (localStorage, 24 h TTL)
 *
 * Fixes applied:
 *   - Portal rendering to escape z-index stacking context of the header
 *   - Budget calculation now restricted to current month (was lifetime)
 *   - Bell badge always visible while unread count > 0
 *   - Smooth animate-fade-in on panel open
 */
import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import {
  Bell, AlertTriangle, TrendingUp, CheckCircle2, X, ChevronRight, Trash2, RefreshCw,
} from 'lucide-react'
import api from '../../services/api.js'
import useAuthStore from '../../store/authStore.js'
import { formatCurrency } from '../../utils/formatters.js'
import { useNavigate } from 'react-router-dom'

// ── Budget thresholds ─────────────────────────────────────────────────────────
const BUDGETS = {
  Food: 10000, Shopping: 8000, Grocery: 5000, Transport: 3000,
  Entertainment: 4000, Utilities: 2000, Rent: 20000, Healthcare: 3000,
}

// ── Notification type config ──────────────────────────────────────────────────
const TYPE_CONFIG = {
  anomaly: {
    icon: AlertTriangle,
    color: 'text-red-400',
    bg: 'bg-red-500/15',
    border: 'border-red-500/20',
    label: 'Anomaly Detected',
  },
  budget: {
    icon: TrendingUp,
    color: 'text-orange-400',
    bg: 'bg-orange-500/15',
    border: 'border-orange-500/20',
    label: 'Budget Alert',
  },
  upload: {
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    border: 'border-emerald-500/20',
    label: 'Upload Complete',
  },
}

// ── Persistence helpers ───────────────────────────────────────────────────────
const DISMISSED_KEY = 'fin_dismissed_notifications'

function getDismissed() {
  try { return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]')) }
  catch { return new Set() }
}
function saveDismissed(set) {
  localStorage.setItem(DISMISSED_KEY, JSON.stringify([...set].slice(-200)))
}

export function addUploadNotification(bank, count) {
  const key = `upload_${Date.now()}`
  const existing = JSON.parse(localStorage.getItem('fin_upload_notifs') || '[]')
  existing.push({ id: key, bank, count, ts: Date.now() })
  localStorage.setItem('fin_upload_notifs', JSON.stringify(existing.slice(-5)))
  // Dispatch a custom event so the NotificationDropdown refreshes immediately
  window.dispatchEvent(new CustomEvent('fin_upload_added'))
}

function getUploadNotifications() {
  try {
    const items = JSON.parse(localStorage.getItem('fin_upload_notifs') || '[]')
    const cutoff = Date.now() - 24 * 60 * 60 * 1000
    return items.filter((n) => n.ts > cutoff)
  } catch { return [] }
}

// ── Single notification row ───────────────────────────────────────────────────
function NotifRow({ notif, onDismiss }) {
  const cfg = TYPE_CONFIG[notif.type] || TYPE_CONFIG.upload
  const Icon = cfg.icon
  return (
    <div
      className={`flex items-start gap-3 px-4 py-3.5
                  border-b border-white/[0.05] last:border-0
                  hover:bg-white/[0.03] transition-colors group cursor-default`}
    >
      <div className={`w-8 h-8 rounded-lg ${cfg.bg} border ${cfg.border} flex items-center justify-center flex-shrink-0 mt-0.5`}>
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-[11px] font-bold uppercase tracking-wider ${cfg.color} mb-0.5`}>
          {cfg.label}
        </p>
        <p className="text-sm text-gray-200 leading-snug">{notif.title}</p>
        {notif.sub && <p className="text-xs text-gray-500 mt-0.5">{notif.sub}</p>}
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDismiss(notif.id) }}
        className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-gray-400
                   transition-all flex-shrink-0 mt-0.5 p-1 rounded hover:bg-white/10"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function NotificationDropdown() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [open, setOpen]       = useState(false)
  const [loading, setLoading] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [dismissed, setDismissed]         = useState(getDismissed)
  const btnRef   = useRef(null)
  const panelRef = useRef(null)

  // Panel position (anchored to bell button)
  const [panelPos, setPanelPos] = useState({ top: 0, right: 0 })

  const updatePos = useCallback(() => {
    if (!btnRef.current) return
    const rect = btnRef.current.getBoundingClientRect()
    setPanelPos({
      top:   rect.bottom + window.scrollY + 8,
      right: window.innerWidth - rect.right + window.scrollX,
    })
  }, [])

  // Close on outside click
  useEffect(() => {
    function h(e) {
      if (
        panelRef.current && !panelRef.current.contains(e.target) &&
        btnRef.current   && !btnRef.current.contains(e.target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  // Listen for upload events from Upload.jsx
  useEffect(() => {
    const handler = () => buildNotifications()
    window.addEventListener('fin_upload_added', handler)
    return () => window.removeEventListener('fin_upload_added', handler)
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const buildNotifications = useCallback(async () => {
    if (!user?.id) return
    setLoading(true)
    const all = []

    // 1. ML Anomalies
    try {
      const { anomalies = [] } = await api.ml.anomalies(user.id, 30)
      anomalies.slice(0, 4).forEach((a) => {
        all.push({
          id:    `anomaly_${a.transaction_id}`,
          type:  'anomaly',
          title: `${a.merchant} — ${formatCurrency(a.amount)}`,
          sub:   a.explanation,
        })
      })
    } catch { /* ignore — models may not be loaded */ }

    // 2. Budget overages — CURRENT MONTH only
    try {
      const now = new Date()
      const monthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
      const { data = [] } = await api.transactions.getAll({ page_size: 200 })
      const catSpend = {}
      data
        .filter((t) => t.type === 'debit' && (t.date || '').startsWith(monthKey))
        .forEach((t) => {
          const c = t.category || 'Other'
          catSpend[c] = (catSpend[c] || 0) + t.amount
        })
      Object.entries(BUDGETS).forEach(([cat, budget]) => {
        const spent = catSpend[cat] || 0
        if (spent > budget * 0.85) {
          const pct = Math.round((spent / budget) * 100)
          all.push({
            id:    `budget_${cat}_${monthKey}`,
            type:  'budget',
            title: `${cat} ${pct >= 100 ? 'budget exceeded' : 'budget almost full'} · ${pct}%`,
            sub:   `${formatCurrency(spent)} of ${formatCurrency(budget)} this month`,
          })
        }
      })
    } catch { /* ignore */ }

    // 3. Recent uploads (from localStorage)
    getUploadNotifications().forEach((u) => {
      all.push({
        id:    u.id,
        type:  'upload',
        title: `${u.count} transactions imported from ${(u.bank || 'bank').toUpperCase()}`,
        sub:   new Date(u.ts).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }),
      })
    })

    setNotifications(all)
    setLoading(false)
  }, [user?.id])

  // Initial fetch
  useEffect(() => { buildNotifications() }, [buildNotifications])

  const visible = useMemo(
    () => notifications.filter((n) => !dismissed.has(n.id)),
    [notifications, dismissed],
  )

  const dismiss = (id) => {
    setDismissed((prev) => {
      const next = new Set([...prev, id])
      saveDismissed(next)
      return next
    })
  }

  const clearAll = () => {
    const ids = new Set([...dismissed, ...visible.map((n) => n.id)])
    saveDismissed(ids)
    setDismissed(ids)
  }

  const unread = visible.length

  const handleOpen = () => {
    updatePos()
    setOpen((o) => {
      if (!o) buildNotifications()
      return !o
    })
  }

  return (
    <>
      {/* Bell button */}
      <button
        ref={btnRef}
        onClick={handleOpen}
        className="relative p-2 rounded-lg text-gray-500 hover:text-gray-200
                   hover:bg-white/[0.06] transition-colors"
        aria-label="Notifications"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Bell className="w-[18px] h-[18px]" />

        {/* Unread badge */}
        {unread > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 text-[9px] font-bold
                       bg-red-500 text-white rounded-full flex items-center justify-center
                       ring-2 ring-[#0d0f1a]"
            style={{ animation: 'pulseGlow 2s ease-in-out infinite' }}
          >
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {/* Dropdown panel — rendered in portal to escape z-index stacking context */}
      {open && createPortal(
        <div
          ref={panelRef}
          style={{
            position: 'absolute',
            top:   panelPos.top,
            right: panelPos.right,
            zIndex: 9999,
          }}
          className="w-80 rounded-2xl border border-white/[0.10]
                     bg-[#13152a]/98 backdrop-blur-xl
                     shadow-[0_24px_64px_rgba(0,0,0,0.75)]
                     animate-fade-in overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.07]">
            <p className="text-sm font-bold text-white flex items-center gap-2">
              Notifications
              {unread > 0 && (
                <span className="px-1.5 py-0.5 text-[10px] bg-red-500/25 text-red-400 rounded-full font-bold border border-red-500/30">
                  {unread}
                </span>
              )}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={buildNotifications}
                disabled={loading}
                className="text-gray-600 hover:text-gray-400 transition-colors p-1 rounded hover:bg-white/[0.06]"
                title="Refresh"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
              {unread > 0 && (
                <button
                  onClick={clearAll}
                  className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1 transition-colors px-2 py-1 rounded hover:bg-white/[0.06]"
                >
                  <Trash2 className="w-3 h-3" /> Clear all
                </button>
              )}
            </div>
          </div>

          {/* Body */}
          <div className="max-h-[380px] overflow-y-auto">
            {loading && notifications.length === 0 ? (
              <div className="py-10 text-center">
                <div className="w-6 h-6 border-2 border-violet-500/40 border-t-violet-400 rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs text-gray-500">Loading notifications…</p>
              </div>
            ) : visible.length === 0 ? (
              <div className="py-12 text-center px-4">
                <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mx-auto mb-3">
                  <Bell className="w-5 h-5 text-gray-700" />
                </div>
                <p className="text-sm text-gray-400 font-medium">You're all caught up!</p>
                <p className="text-xs text-gray-600 mt-1">No new alerts right now.</p>
              </div>
            ) : (
              visible.map((n) => (
                <NotifRow key={n.id} notif={n} onDismiss={dismiss} />
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-white/[0.07] px-4 py-3 bg-white/[0.01]">
            <button
              onClick={() => { setOpen(false); navigate('/insights') }}
              className="w-full flex items-center justify-center gap-1.5 text-xs text-violet-400
                         hover:text-violet-300 font-semibold transition-colors py-1"
            >
              View ML Insights <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>,
        document.body,
      )}

      {/* Inline keyframe for badge glow (avoids Tailwind conflict) */}
      <style>{`
        @keyframes pulseGlow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }
          50%       { box-shadow: 0 0 0 4px rgba(239,68,68,0); }
        }
      `}</style>
    </>
  )
}
