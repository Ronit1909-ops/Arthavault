import React, { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowUpRight, ArrowDownRight, IndianRupee, ReceiptText, ShoppingBag,
  Activity, Upload, RefreshCw,
} from 'lucide-react'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  XAxis, YAxis, CartesianGrid, Area, AreaChart,
} from 'recharts'
import Card from '../components/common/Card.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import ErrorMessage from '../components/common/ErrorMessage.jsx'
import api from '../services/api.js'
import { formatCurrency, formatDate, getCategoryHex } from '../utils/formatters.js'
import useAuthStore from '../store/authStore.js'

// Categories that should NOT appear as "top category"
const UNCATEGORIZED_LABELS = new Set([
  'Uncategorized', 'uncategorized', 'Other', 'other',
  'Miscellaneous', 'miscellaneous', 'Unknown', 'unknown',
])

// ── Summary card ─────────────────────────────────────────────────────────────
function SummaryCard({ title, value, icon: Icon, gradient, trendValue, sub }) {
  const up = trendValue >= 0
  return (
    <Card className={`${gradient} border-0 text-white relative overflow-hidden`}>
      {/* Glow orb */}
      <div className="absolute -top-4 -right-4 w-24 h-24 rounded-full bg-white/10 blur-2xl pointer-events-none" />
      <div className="flex items-start justify-between relative z-10">
        <div>
          <p className="text-sm font-medium opacity-75">{title}</p>
          <p className="text-2xl font-bold mt-1 tracking-tight">{value}</p>
          {trendValue !== undefined && (
            <p className={`flex items-center gap-0.5 text-xs mt-1.5 opacity-85`}>
              {up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
              {Math.abs(trendValue)}% vs last month
            </p>
          )}
          {sub && <p className="text-xs mt-1 opacity-70">{sub}</p>}
        </div>
        <div className="w-11 h-11 rounded-xl bg-white/20 flex items-center justify-center shadow-inner">
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </Card>
  )
}

// ── Custom pie tooltip ────────────────────────────────────────────────────────
function PieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { name, value } = payload[0]
  return (
    <div className="rounded-xl border border-white/[0.12] bg-[#1a1d2e]/98 backdrop-blur-sm px-3 py-2 text-sm shadow-2xl">
      <p className="font-semibold text-white">{name}</p>
      <p className="text-gray-300 mt-0.5">{formatCurrency(value)}</p>
    </div>
  )
}

// ── Area/Line tooltip ─────────────────────────────────────────────────────────
function AreaTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-white/[0.12] bg-[#1a1d2e]/98 backdrop-blur-sm px-3 py-2 text-sm shadow-2xl min-w-[140px]">
      <p className="font-semibold text-gray-300 mb-2">{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center justify-between gap-4">
          <span style={{ color: p.color }} className="text-xs font-medium">{p.name}</span>
          <span className="text-white font-bold">{formatCurrency(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

// ── Custom dot for area chart ─────────────────────────────────────────────────
function CustomDot({ cx, cy, value }) {
  if (!value) return null
  return (
    <circle
      cx={cx} cy={cy} r={4}
      fill="#7c3aed"
      stroke="#0f1117"
      strokeWidth={2}
    />
  )
}

export default function Dashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [txns, setTxns]           = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.transactions.getAll({ page_size: 200 })
      setTxns(res.data || [])
      setLastUpdated(new Date())
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()

    // Refetch when another tab/page triggers a category update
    const onStorageEvent = (e) => {
      if (e.key === 'arthavault_category_updated') fetchData()
    }
    window.addEventListener('storage', onStorageEvent)
    return () => window.removeEventListener('storage', onStorageEvent)
  }, [])

  // ── Derived metrics ─────────────────────────────────────────────────────────
  const metrics = useMemo(() => {
    const debits  = txns.filter((t) => t.type === 'debit')
    const credits = txns.filter((t) => t.type === 'credit')
    const totalSpend  = debits.reduce((s, t) => s + t.amount, 0)
    const totalIncome = credits.reduce((s, t) => s + t.amount, 0)

    // This month vs last month for trend
    const now = new Date()
    const thisMonthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const lastMonthDate = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const lastMonthKey = `${lastMonthDate.getFullYear()}-${String(lastMonthDate.getMonth() + 1).padStart(2, '0')}`
    const thisMonthSpend = debits
      .filter((t) => (t.date || '').startsWith(thisMonthKey))
      .reduce((s, t) => s + t.amount, 0)
    const lastMonthSpend = debits
      .filter((t) => (t.date || '').startsWith(lastMonthKey))
      .reduce((s, t) => s + t.amount, 0)
    const spendTrend = lastMonthSpend > 0
      ? Math.round(((thisMonthSpend - lastMonthSpend) / lastMonthSpend) * 100)
      : 0

    // Distinct months (for the "X month(s) of data" card) — Bug 2 fix
    const distinctMonths = [
      ...new Set(debits.map((t) => (t.date || '').slice(0, 7)).filter(Boolean))
    ]
    const monthsOfData = distinctMonths.length

    // Category breakdown (ALL categories, including Uncategorized — for pie chart)
    const catMap = {}
    debits.forEach((t) => {
      const c = t.category || 'Uncategorized'
      catMap[c] = (catMap[c] || 0) + t.amount
    })
    const categoryData = Object.entries(catMap)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)

    // Top category — Bug 3 fix: exclude Uncategorized/Other labels
    const topCategory = categoryData.find((c) => !UNCATEGORIZED_LABELS.has(c.name)) || null

    // ── Trend data: daily if ≤ 2 months, monthly if 3+ months ──────────────────
    const useDaily = distinctMonths.length <= 2

    let trendData = []
    let trendLabel = ''

    if (useDaily) {
      // Daily grouping — gives a real curve even for single-month data
      const dayMap = {}
      debits.forEach((t) => {
        const d = new Date(t.date)
        if (isNaN(d.getTime())) return
        const key   = (t.date || '').slice(0, 10)                             // YYYY-MM-DD
        const label = d.toLocaleString('en-IN', { day: 'numeric', month: 'short' }) // "5 Feb"
        if (!dayMap[key]) dayMap[key] = { key, label, amount: 0, count: 0 }
        dayMap[key].amount += Number(t.amount) || 0
        dayMap[key].count  += 1
      })
      trendData  = Object.values(dayMap)
        .sort((a, b) => a.key.localeCompare(b.key))
        .map((m) => ({ ...m, amount: Math.round(m.amount) }))
      trendLabel = `Daily · ${monthsOfData} month(s) of data`
    } else {
      // Monthly grouping for 3+ months
      const monthMap = {}
      debits.forEach((t) => {
        const d = new Date(t.date)
        if (isNaN(d.getTime())) return
        const key   = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
        const label = d.toLocaleString('en-IN', { month: 'short', year: '2-digit' })
        if (!monthMap[key]) monthMap[key] = { key, label, amount: 0, count: 0 }
        monthMap[key].amount += Number(t.amount) || 0
        monthMap[key].count  += 1
      })
      trendData  = Object.values(monthMap)
        .sort((a, b) => a.key.localeCompare(b.key))
        .slice(-6)
        .map((m) => ({ ...m, amount: Math.round(m.amount) }))
      trendLabel = `Last ${trendData.length} months · debit transactions`
    }

    // Y-axis domain for area chart — add 20% headroom
    const maxAmount = trendData.reduce((m, d) => Math.max(m, d.amount), 0)
    const yMax = Math.ceil((maxAmount * 1.25) / 1000) * 1000 || 10000

    // Top merchants
    const merchantMap = {}
    debits.forEach((t) => {
      const m = t.merchant || 'Unknown'
      if (!merchantMap[m]) merchantMap[m] = { merchant: m, category: t.category, total: 0, count: 0 }
      merchantMap[m].total  += t.amount
      merchantMap[m].count  += 1
    })
    const topMerchants = Object.values(merchantMap)
      .sort((a, b) => b.total - a.total)
      .slice(0, 5)

    return {
      totalSpend, totalIncome, categoryData, topCategory, trendData, topMerchants,
      txnCount: txns.length, spendTrend, yMax, trendLabel, useDaily,
      thisMonthSpend, lastMonthSpend, monthsOfData,
    }
  }, [txns])

  if (loading) return (
    <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>
  )
  if (error) return <ErrorMessage message={error} onRetry={fetchData} />

  // ── Empty state ─────────────────────────────────────────────────────────────
  if (txns.length === 0) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Dashboard</h1>
            <p className="text-gray-400 text-sm mt-0.5">Welcome back, {user?.name?.split(' ')[0]}! 👋</p>
          </div>
        </div>
        <div className="flex flex-col items-center justify-center py-24 gap-5">
          <div className="w-20 h-20 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center">
            <ReceiptText className="w-10 h-10 text-violet-500/60" />
          </div>
          <div className="text-center">
            <p className="text-white font-semibold text-lg">No transactions yet</p>
            <p className="text-gray-500 text-sm mt-1">Upload your bank statement to get started</p>
          </div>
          <button
            id="dashboard-upload-btn"
            onClick={() => navigate('/upload')}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-violet-600 to-indigo-600
                       text-white font-semibold rounded-xl shadow-[0_0_24px_rgba(124,58,237,0.4)]
                       hover:shadow-[0_0_32px_rgba(124,58,237,0.6)] transition-all duration-200"
          >
            <Upload className="w-4 h-4" />
            Upload Statement
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 text-sm mt-0.5">Welcome back, {user?.name?.split(' ')[0]}! 👋</p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <p className="text-xs text-gray-600">
              Last updated:{' '}
              <span className="text-gray-500">
                {lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            </p>
          )}
          <button
            id="dashboard-refresh-btn"
            onClick={fetchData}
            className="p-2 rounded-lg text-gray-500 hover:text-violet-400 hover:bg-violet-500/10 transition-all"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <SummaryCard
          title="Total Spend"
          value={formatCurrency(metrics.totalSpend)}
          icon={IndianRupee}
          gradient="bg-gradient-to-br from-violet-600 to-indigo-700"
          trendValue={metrics.spendTrend}
        />
        <SummaryCard
          title="Total Income"
          value={formatCurrency(metrics.totalIncome)}
          icon={ArrowUpRight}
          gradient="bg-gradient-to-br from-emerald-500 to-teal-700"
        />
        {/* Bug 2 fix: use monthsOfData (distinct months), not trendData.length (chart points) */}
        <SummaryCard
          title="Transactions"
          value={metrics.txnCount.toLocaleString()}
          icon={ReceiptText}
          gradient="bg-gradient-to-br from-blue-500 to-blue-700"
          sub={`${metrics.monthsOfData} month(s) of data`}
        />
        {/* Bug 3 fix: show real top category, not Uncategorized */}
        <SummaryCard
          title="Top Category"
          value={metrics.topCategory ? metrics.topCategory.name : 'Not enough data'}
          icon={ShoppingBag}
          gradient="bg-gradient-to-br from-orange-500 to-rose-600"
          sub={
            metrics.topCategory
              ? formatCurrency(metrics.topCategory.value)
              : 'Tag some transactions to see your top category'
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* ── Monthly Spending Trend ── */}
        <Card className="lg:col-span-3">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-violet-400" />
                {metrics.useDaily ? 'Daily' : 'Monthly'} Spending Trend
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">{metrics.trendLabel}</p>
            </div>
            {metrics.trendData.length >= 2 && (
              <div className="text-right">
                <p className="text-xs text-gray-500">This month</p>
                <p className="text-sm font-bold text-violet-300">{formatCurrency(metrics.thisMonthSpend)}</p>
              </div>
            )}
          </div>

          {metrics.trendData.length === 0 ? (
            <div className="h-52 flex flex-col items-center justify-center gap-2">
              <Activity className="w-10 h-10 text-violet-800/60" />
              <p className="text-gray-500 text-sm">No data · Upload a statement to see your spending curve</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart
                data={metrics.trendData}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#7c3aed" stopOpacity={0.55} />
                    <stop offset="60%"  stopColor="#7c3aed" stopOpacity={0.20} />
                    <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: '#6b7280', fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  dy={6}
                  interval={metrics.useDaily ? Math.max(Math.floor(metrics.trendData.length / 8), 0) : 0}
                />
                <YAxis
                  domain={[0, metrics.yMax]}
                  tickFormatter={(v) => v >= 100000 ? `₹${(v / 100000).toFixed(1)}L` : `₹${(v / 1000).toFixed(0)}K`}
                  tick={{ fontSize: 11, fill: '#6b7280' }}
                  width={58}
                  axisLine={false}
                  tickLine={false}
                  tickCount={5}
                />
                <Tooltip content={<AreaTooltip />} cursor={{ stroke: 'rgba(124,58,237,0.3)', strokeWidth: 2 }} />
                <Area
                  type="monotone"
                  dataKey="amount"
                  stroke="#7c3aed"
                  strokeWidth={3}
                  fill="url(#spendGrad)"
                  name="Spend"
                  dot={<CustomDot />}
                  activeDot={{ r: 6, fill: '#7c3aed', stroke: '#0f1117', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Category pie */}
        <Card className="lg:col-span-2">
          <h2 className="text-base font-semibold text-white mb-1">By Category</h2>
          <p className="text-xs text-gray-500 mb-4">Spending breakdown</p>
          {metrics.categoryData.length === 0 ? (
            <div className="h-52 flex items-center justify-center text-gray-500 text-sm">No data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={230}>
              <PieChart>
                <Pie
                  data={metrics.categoryData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="44%"
                  outerRadius={78}
                  innerRadius={36}
                  paddingAngle={2}
                  strokeWidth={0}
                >
                  {metrics.categoryData.map((entry) => (
                    <Cell key={entry.name} fill={getCategoryHex(entry.name)} />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
                <Legend
                  iconType="circle"
                  iconSize={7}
                  wrapperStyle={{ paddingTop: '6px' }}
                  formatter={(v) => (
                    <span style={{ color: '#9ca3af', fontSize: '11px' }}>{v}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* Top merchants */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-white">Top Merchants</h2>
            <p className="text-xs text-gray-500 mt-0.5">Highest spending destinations</p>
          </div>
          <button
            onClick={() => navigate('/transactions')}
            className="text-sm text-violet-400 hover:text-violet-300 font-semibold transition-colors"
          >
            View all →
          </button>
        </div>
        {metrics.topMerchants.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">No transactions yet. Upload a statement!</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] font-bold text-gray-600 uppercase tracking-widest border-b border-white/[0.06]">
                  <th className="pb-3 pr-4">#</th>
                  <th className="pb-3 pr-4">Merchant</th>
                  <th className="pb-3 pr-4">Category</th>
                  <th className="pb-3 pr-4 text-right">Total Spend</th>
                  <th className="pb-3 text-right">Txns</th>
                </tr>
              </thead>
              <tbody>
                {metrics.topMerchants.map((m, i) => (
                  <tr
                    key={m.merchant}
                    onClick={() => navigate(`/transactions?merchant=${encodeURIComponent(m.merchant)}`)}
                    className="border-b border-white/[0.04] hover:bg-white/[0.03] cursor-pointer transition-colors"
                  >
                    <td className="py-3 pr-4 text-gray-600 font-bold">{i + 1}</td>
                    <td className="py-3 pr-4 font-semibold text-gray-100">{m.merchant}</td>
                    <td className="py-3 pr-4">
                      <span className="px-2 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.08] text-xs text-gray-400">
                        {m.category || 'Other'}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-right font-bold text-red-400">{formatCurrency(m.total)}</td>
                    <td className="py-3 text-right text-gray-500">{m.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
