import React from 'react'
import { IndianRupee, Sparkles, Shield, TrendingUp, ArrowRight, Zap } from 'lucide-react'
import api from '../services/api.js'

const features = [
  { icon: TrendingUp, label: 'Spending Analytics',  desc: 'Beautiful charts & category breakdowns',    color: 'text-blue-400',   bg: 'bg-blue-500/10'   },
  { icon: Sparkles,   label: 'AI Categorisation',   desc: 'Auto-tag transactions with XGBoost models', color: 'text-violet-400', bg: 'bg-violet-500/10' },
  { icon: Shield,     label: 'Anomaly Detection',   desc: 'Get alerted on suspicious transactions',    color: 'text-emerald-400',bg: 'bg-emerald-500/10'},
  { icon: Zap,        label: 'Prophet Forecasting', desc: 'Predict next month spending with ML',       color: 'text-orange-400', bg: 'bg-orange-500/10' },
]

const banks = ['SBI', 'HDFC', 'ICICI', 'Bank of Baroda', 'IDBI', 'Kotak', 'Central Bank']

export default function Login() {
  const handleLogin = () => api.auth.login()

  return (
    <div className="min-h-screen flex bg-[#0a0c14] overflow-hidden relative">
      {/* Ambient orbs */}
      <div className="absolute w-[600px] h-[600px] -top-32 -left-32 rounded-full
                      bg-violet-700/20 blur-[120px] pointer-events-none" />
      <div className="absolute w-[400px] h-[400px] bottom-0 right-0 rounded-full
                      bg-blue-700/15 blur-[100px] pointer-events-none" />
      <div className="absolute w-[300px] h-[300px] top-1/2 left-1/2 rounded-full
                      bg-indigo-600/10 blur-[80px] pointer-events-none" />

      {/* ── Left branding panel ───────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[55%] flex-col justify-between p-12 relative z-10">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600
                         flex items-center justify-center shadow-[0_0_20px_rgba(109,40,217,0.6)]">
            <IndianRupee className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white tracking-tight">UPI Finance Tracker</span>
        </div>

        {/* Hero text */}
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
                          bg-violet-500/10 border border-violet-500/20 text-violet-300
                          text-xs font-semibold mb-6">
            <Sparkles className="w-3 h-3" /> Powered by Machine Learning
          </div>
          <h1 className="text-5xl font-extrabold leading-[1.1] text-white mb-4">
            Take control of<br />
            <span className="bg-gradient-to-r from-violet-400 via-indigo-400 to-blue-400
                             bg-clip-text text-transparent">
              your UPI spending
            </span>
          </h1>
          <p className="text-gray-400 text-lg mb-10 leading-relaxed">
            Upload bank statements, get AI-powered insights,<br />
            and track every rupee automatically.
          </p>

          {/* Feature cards */}
          <div className="grid grid-cols-2 gap-3 mb-10">
            {features.map(({ icon: Icon, label, desc, color, bg }) => (
              <div key={label}
                   className="flex items-start gap-3 p-4 rounded-2xl border border-white/[0.06]
                              bg-white/[0.03] backdrop-blur-sm hover:bg-white/[0.05] transition-all">
                <div className={`w-8 h-8 rounded-xl ${bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-4 h-4 ${color}`} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{label}</p>
                  <p className="text-[11px] text-gray-500 leading-snug mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Supported banks */}
          <div>
            <p className="text-xs text-gray-600 uppercase tracking-widest mb-2">Supported Banks</p>
            <div className="flex flex-wrap gap-2">
              {banks.map((b) => (
                <span key={b} className="px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]
                                         text-xs text-gray-400 font-medium">{b}</span>
              ))}
            </div>
          </div>
        </div>

        <p className="text-xs text-gray-700">© 2026 UPI Finance Tracker · Secure · Private · Fast</p>
      </div>

      {/* ── Right login panel ─────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 relative z-10">
        {/* Card */}
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600
                           flex items-center justify-center">
              <IndianRupee className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-white">UPI Finance Tracker</span>
          </div>

          <div className="rounded-3xl border border-white/[0.08] bg-white/[0.04] backdrop-blur-2xl
                          shadow-[0_24px_80px_rgba(0,0,0,0.6)] p-8">
            <h2 className="text-2xl font-bold text-white mb-1">Welcome back</h2>
            <p className="text-gray-400 text-sm mb-8">Sign in with your Google account to continue</p>

            <button
              id="google-signin-btn"
              onClick={handleLogin}
              className="w-full flex items-center justify-center gap-3 px-5 py-3.5
                         bg-white hover:bg-gray-50 active:bg-gray-100
                         text-gray-700 text-sm font-semibold rounded-2xl
                         shadow-[0_4px_16px_rgba(0,0,0,0.3)]
                         hover:shadow-[0_8px_24px_rgba(0,0,0,0.4)]
                         transition-all duration-200 active:scale-[0.98]"
            >
              <svg viewBox="0 0 24 24" className="w-5 h-5" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            <div className="mt-6 pt-6 border-t border-white/[0.06]">
              <div className="flex justify-center gap-6">
                {[
                  { icon: Shield,     label: 'Secure' },
                  { icon: Sparkles,   label: 'AI-Powered' },
                  { icon: TrendingUp, label: 'Insightful' },
                ].map(({ icon: Icon, label }) => (
                  <div key={label} className="flex flex-col items-center gap-1">
                    <Icon className="w-4 h-4 text-violet-400" />
                    <span className="text-[10px] text-gray-600 font-medium">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <p className="mt-5 text-xs text-gray-700 text-center">
            By signing in, you agree to our terms. We only read your email & name.
          </p>
        </div>
      </div>
    </div>
  )
}
