import React, { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts'
import {
  AlertTriangle, CheckCircle2, TrendingUp, Brain, X,
  Target, Zap, Activity, Calendar,
} from 'lucide-react'
import Card from '../components/common/Card.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import ErrorMessage from '../components/common/ErrorMessage.jsx'
import api from '../services/api.js'
import useAuthStore from '../store/authStore.js'
import { formatCurrency, formatDate, getCategoryColor } from '../utils/formatters.js'

// ── Custom Tooltip (dark theme) ────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-white/[0.12] bg-[#1a1d2e]/98 backdrop-blur-sm px-3 py-2.5 text-xs shadow-2xl min-w-[160px]">
      <p className="font-semibold text-gray-300 mb-2">{label}</p>
      {payload.map((p) => {
        if (p.name === 'upper_bound' || p.name === 'Confidence Band') return null
        return (
          <div key={p.name} className="flex items-center justify-between gap-4 mb-1">
            <span className="text-gray-400 font-medium">{p.name}</span>
            <span className="text-white font-bold">{formatCurrency(p.value)}</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Anomaly card ───────────────────────────────────────────────────────────────
function AnomalyCard({ item, onDismiss }) {
  return (
    <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl hover:bg-red-500/15 transition-colors">
      <div className="w-9 h-9 rounded-xl bg-red-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
        <AlertTriangle className="w-4 h-4 text-red-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-white text-sm">{item.merchant}</p>
          <button
            onClick={() => onDismiss(item.transaction_id)}
            className="text-gray-600 hover:text-gray-400 flex-shrink-0 transition-colors p-0.5 rounded hover:bg-white/10"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-sm font-bold text-red-400">{formatCurrency(item.amount)}</span>
          <span className="text-xs text-gray-500">•</span>
          <span className="text-xs text-gray-400">{formatDate(item.date)}</span>
        </div>
        <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">{item.explanation}</p>
        <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-red-500/15 border border-red-500/25">
          <Activity className="w-3 h-3 text-red-400" />
          <span className="text-[11px] text-red-400 font-semibold">
            Score: {item.anomaly_score?.toFixed(3)}
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Budget thresholds ──────────────────────────────────────────────────────────
const BUDGETS = {
  Food: 10000, Shopping: 8000, Grocery: 5000, Transport: 3000,
  Entertainment: 4000, Utilities: 2000, Rent: 20000, Healthcare: 3000,
}

// ── Budget progress bar ────────────────────────────────────────────────────────
function BudgetBar({ category, spent }) {
  const budget   = BUDGETS[category] || 5000
  const pct      = Math.min((spent / budget) * 100, 100)
  const over     = spent > budget
  const barColor = pct < 70 ? '#22c55e' : pct < 90 ? '#f59e0b' : '#ef4444'

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-200">{category}</span>
        <div className="text-right">
          <span className={`text-sm font-bold ${over ? 'text-red-400' : 'text-gray-100'}`}>
            {formatCurrency(spent)}
          </span>
          <span className="text-xs text-gray-500"> / {formatCurrency(budget)}</span>
          <span className={`ml-2 text-xs font-bold px-1.5 py-0.5 rounded-full ${
            pct >= 100 ? 'bg-red-500/20 text-red-400' :
            pct >= 90  ? 'bg-yellow-500/20 text-yellow-400' :
                         'bg-green-500/20 text-green-400'
          }`}>
            {pct.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="w-full bg-white/[0.06] rounded-full h-2.5 overflow-hidden">
        <div
          className="h-2.5 rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: barColor, boxShadow: `0 0 8px ${barColor}60` }}
        />
      </div>
    </div>
  )
}

// ── Forecast summary stat ──────────────────────────────────────────────────────
function ForecastStat({ label, value, sub, icon: Icon, color }) {
  return (
    <div className={`flex items-center gap-3 p-3 rounded-xl border ${color.border} ${color.bg}`}>
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color.iconBg}`}>
        <Icon className={`w-4 h-4 ${color.icon}`} />
      </div>
      <div>
        <p className="text-xs text-gray-400 font-medium">{label}</p>
        <p className={`text-sm font-bold ${color.text}`}>{value}</p>
        {sub && <p className="text-[11px] text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Insights() {
  const { user } = useAuthStore()
  const [forecast, setForecast]   = useState(null)
  const [anomalies, setAnomalies] = useState([])
  const [dismissed, setDismissed] = useState(new Set())
  const [txns, setTxns]           = useState([])
  const [forecastLoading, setFL]  = useState(true)
  const [anomalyLoading, setAL]   = useState(true)
  const [forecastError, setFE]    = useState(null)
  const [anomalyError, setAE]     = useState(null)
  const [mlHealth, setMlHealth]   = useState(null)

  useEffect(() => {
    if (!user?.id) return

    // Forecast
    setFL(true)
    api.ml.forecast(user.id, 30)
      .then((d) => { setForecast(d); setFE(null) })
      .catch((e) => {
        if (e.response?.status === 404) {
          setForecast({ forecast: [], total_predicted: 0, confidence_interval: '80%' })
          setFE(null)
        } else {
          setFE(e.response?.data?.detail || 'Forecast unavailable')
        }
      })
      .finally(() => setFL(false))

    // Anomalies
    setAL(true)
    api.ml.anomalies(user.id, 30)
      .then((d) => { setAnomalies(d.anomalies || []); setAE(null) })
      .catch((e) => setAE(e.response?.data?.detail || 'Anomaly data unavailable'))
      .finally(() => setAL(false))

    // ML health
    api.ml.health().then(setMlHealth).catch(() => {})

    // Transactions for budget bars (current month)
    api.transactions.getAll({ page_size: 200 })
      .then((r) => setTxns(r.data || []))
      .catch(() => {})
  }, [user?.id])

  // ── Budget: use CURRENT month transactions only ──────────────────────────────
  const catSpend = useMemo(() => {
    const now = new Date()
    const thisMonthKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const spend = {}
    txns
      .filter((t) => t.type === 'debit' && (t.date || '').startsWith(thisMonthKey))
      .forEach((t) => {
        const c = t.category || 'Other'
        spend[c] = (spend[c] || 0) + t.amount
      })
    return spend
  }, [txns])

  // ── Forecast chart data: enrich with formatted label ────────────────────────
  const forecastChartData = useMemo(() => {
    if (!forecast?.forecast?.length) return []
    return forecast.forecast.map((row) => ({
      ...row,
      label: row.date ? row.date.slice(5) : '', // MM-DD
      band: row.upper_bound - row.lower_bound,   // confidence band width
    }))
  }, [forecast])

  // Forecast Y-axis max
  const forecastYMax = useMemo(() => {
    if (!forecastChartData.length) return 10000
    const max = Math.max(...forecastChartData.map((d) => d.upper_bound || d.predicted_spend || 0))
    return Math.ceil((max * 1.15) / 1000) * 1000 || 10000
  }, [forecastChartData])

  const visibleAnomalies = anomalies.filter((a) => !dismissed.has(a.transaction_id))
  const totalPredicted = forecast?.total_predicted || 0
  const avgDaily = forecastChartData.length > 0
    ? totalPredicted / forecastChartData.length
    : 0
  const peakDay = forecastChartData.reduce((max, d) =>
    (d.predicted_spend || 0) > (max.predicted_spend || 0) ? d : max,
    forecastChartData[0] || {}
  )

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">ML Insights</h1>
          <p className="text-gray-400 text-sm mt-0.5">AI-powered spending analysis &amp; anomaly detection</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {mlHealth && (
            <div className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border ${
              mlHealth.models_loaded
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25'
                : 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25'
            }`}>
              <Brain className="w-3.5 h-3.5" />
              ML {mlHealth.models_loaded ? 'ready' : 'degraded'}
            </div>
          )}
        </div>
      </div>

      {/* ── Forecast chart ── */}
      <Card>
        <div className="flex items-center justify-between flex-wrap gap-2 mb-5">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-orange-400" />
              30-Day Spending Forecast
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">Prophet time-series model · 80% confidence interval</p>
          </div>
          {forecast && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-500 px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                Confidence: <span className="text-orange-400 font-bold">{forecast.confidence_interval}</span>
              </span>
            </div>
          )}
        </div>

        {forecastLoading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <LoadingSpinner size="lg" />
            <p className="text-gray-500 text-sm">Generating forecast…</p>
          </div>
        ) : forecastError ? (
          <ErrorMessage message={forecastError} />
        ) : !forecastChartData.length ? (
          <div className="py-14 text-center">
            <div className="w-16 h-16 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center mx-auto mb-4">
              <TrendingUp className="w-8 h-8 text-orange-500/60" />
            </div>
            <p className="text-white font-semibold text-sm mb-1">No forecast data yet</p>
            <p className="text-gray-500 text-xs mb-5">
              Upload a bank statement to generate your personalised 30-day spending forecast.
            </p>
            <Link
              to="/upload"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-orange-500 to-rose-500
                         text-white text-sm font-semibold rounded-xl shadow-[0_0_20px_rgba(249,115,22,0.35)]
                         hover:shadow-[0_0_28px_rgba(249,115,22,0.5)] transition-all duration-200"
            >
              Upload Statement
            </Link>
          </div>
        ) : (
          <>
            {/* Summary stats row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
              <ForecastStat
                label="Total Predicted (30 days)"
                value={formatCurrency(totalPredicted)}
                icon={Target}
                color={{
                  bg: 'bg-orange-500/8',
                  border: 'border-orange-500/20',
                  iconBg: 'bg-orange-500/15',
                  icon: 'text-orange-400',
                  text: 'text-orange-300',
                }}
              />
              <ForecastStat
                label="Avg Daily Spend"
                value={formatCurrency(avgDaily)}
                icon={Calendar}
                color={{
                  bg: 'bg-blue-500/8',
                  border: 'border-blue-500/20',
                  iconBg: 'bg-blue-500/15',
                  icon: 'text-blue-400',
                  text: 'text-blue-300',
                }}
              />
              <ForecastStat
                label="Peak Day"
                value={peakDay?.label ? `${peakDay.label} · ${formatCurrency(peakDay.predicted_spend)}` : '—'}
                icon={Zap}
                color={{
                  bg: 'bg-violet-500/8',
                  border: 'border-violet-500/20',
                  iconBg: 'bg-violet-500/15',
                  icon: 'text-violet-400',
                  text: 'text-violet-300',
                }}
              />
            </div>

            {/* Chart */}
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart
                data={forecastChartData}
                margin={{ top: 10, right: 8, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#f97316" stopOpacity={0.50} />
                    <stop offset="60%"  stopColor="#f97316" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#f97316" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%"   stopColor="#f97316" stopOpacity={0.12} />
                    <stop offset="100%" stopColor="#f97316" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                  axisLine={false}
                  tickLine={false}
                  interval={Math.floor(forecastChartData.length / 6)}
                  dy={4}
                />
                <YAxis
                  domain={[0, forecastYMax]}
                  tickFormatter={(v) => v >= 100000 ? `₹${(v / 100000).toFixed(1)}L` : `₹${(v / 1000).toFixed(0)}K`}
                  tick={{ fontSize: 10, fill: '#6b7280' }}
                  width={58}
                  axisLine={false}
                  tickLine={false}
                  tickCount={5}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(249,115,22,0.3)', strokeWidth: 2 }} />

                {/* Confidence band as area between upper and lower */}
                <Area
                  type="monotone"
                  dataKey="upper_bound"
                  stroke="none"
                  fill="url(#confGrad)"
                  name="Confidence Band"
                  legendType="none"
                />
                <Area
                  type="monotone"
                  dataKey="lower_bound"
                  stroke="none"
                  fill="#0f1117"
                  legendType="none"
                  name="lower_fill"
                />

                {/* Main forecast line */}
                <Area
                  type="monotone"
                  dataKey="predicted_spend"
                  stroke="#f97316"
                  strokeWidth={2.5}
                  fill="url(#forecastGrad)"
                  name="Predicted Spend"
                  dot={false}
                  activeDot={{ r: 5, fill: '#f97316', stroke: '#0f1117', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>

            <div className="flex items-center justify-end gap-4 mt-2 pt-3 border-t border-white/[0.05]">
              <div className="flex items-center gap-1.5">
                <div className="w-8 h-0.5 bg-orange-500 rounded" />
                <span className="text-xs text-gray-500">Predicted spend</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-8 h-3 bg-orange-500/15 rounded" />
                <span className="text-xs text-gray-500">80% confidence band</span>
              </div>
            </div>
          </>
        )}
      </Card>

      {/* Anomalies + Budget */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Anomaly alerts */}
        <Card>
          <div className="flex items-center gap-2 mb-5">
            <div className="w-8 h-8 rounded-lg bg-red-500/15 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4 text-red-400" />
            </div>
            <div className="flex-1">
              <h2 className="text-base font-bold text-white">Anomaly Alerts</h2>
              <p className="text-xs text-gray-500">Unusual spending in last 30 days</p>
            </div>
            {visibleAnomalies.length > 0 && (
              <span className="px-2.5 py-1 text-xs font-bold bg-red-500/20 text-red-400 rounded-full border border-red-500/25">
                {visibleAnomalies.length}
              </span>
            )}
          </div>

          {anomalyLoading ? (
            <div className="flex flex-col items-center justify-center py-10 gap-3">
              <LoadingSpinner />
              <p className="text-gray-500 text-xs">Running anomaly detection…</p>
            </div>
          ) : anomalyError ? (
            <ErrorMessage message={anomalyError} />
          ) : visibleAnomalies.length === 0 ? (
            <div className="py-10 text-center">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 className="w-6 h-6 text-emerald-400" />
              </div>
              <p className="text-white font-semibold text-sm">All clear!</p>
              <p className="text-gray-500 text-xs mt-1">No anomalies detected in the last 30 days 🎉</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
              {visibleAnomalies.map((a) => (
                <AnomalyCard
                  key={a.transaction_id}
                  item={a}
                  onDismiss={(id) => setDismissed((s) => new Set([...s, id]))}
                />
              ))}
            </div>
          )}
        </Card>

        {/* Budget progress */}
        <Card>
          <div className="flex items-center gap-2 mb-5">
            <div className="w-8 h-8 rounded-lg bg-blue-500/15 flex items-center justify-center">
              <Target className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Category Budgets</h2>
              <p className="text-xs text-gray-500">Current month spending vs limits</p>
            </div>
          </div>

          {Object.keys(catSpend).length === 0 ? (
            <div className="py-10 text-center">
              <Target className="w-10 h-10 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-400 text-sm font-medium">No spending this month yet</p>
              <p className="text-gray-600 text-xs mt-1">Budget bars appear once you have transactions</p>
            </div>
          ) : (
            <div className="space-y-5 max-h-[360px] overflow-y-auto pr-1">
              {Object.entries(BUDGETS)
                .filter(([c]) => catSpend[c] !== undefined)
                .map(([category]) => (
                  <BudgetBar key={category} category={category} spent={catSpend[category] || 0} />
                ))}
              {Object.entries(catSpend)
                .filter(([c]) => !BUDGETS[c] && c !== 'Uncategorized')
                .map(([category, spent]) => (
                  <BudgetBar key={category} category={category} spent={spent} />
                ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
