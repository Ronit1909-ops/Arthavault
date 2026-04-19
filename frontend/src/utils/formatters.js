import { format, parseISO, isValid } from 'date-fns'

/** Format a number as Indian Rupees: ₹1,23,456.78 */
export function formatCurrency(amount) {
  if (amount == null || isNaN(amount)) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount)
}

/** Format a date string/Date as "22 Jun 2024" */
export function formatDate(date) {
  if (!date) return '—'
  const d = typeof date === 'string' ? parseISO(date) : date
  return isValid(d) ? format(d, 'd MMM yyyy') : '—'
}

/** Format a date string/Date as "22 Jun 2024, 3:45 PM" */
export function formatDateTime(date) {
  if (!date) return '—'
  const d = typeof date === 'string' ? parseISO(date) : date
  return isValid(d) ? format(d, 'd MMM yyyy, h:mm a') : '—'
}

/** Format short month e.g. "Jan 2024" */
export function formatMonth(date) {
  if (!date) return '—'
  const d = typeof date === 'string' ? parseISO(date) : date
  return isValid(d) ? format(d, 'MMM yyyy') : '—'
}

/**
 * Returns Tailwind color classes { bg, text, dot } for a spending category.
 * Falls back gracefully for any unknown category name.
 */
export function getCategoryColor(category) {
  const map = {
    food:          { bg: 'bg-red-500/20',    text: 'text-red-400',    dot: 'bg-red-500'    },
    shopping:      { bg: 'bg-blue-500/20',   text: 'text-blue-400',   dot: 'bg-blue-500'   },
    grocery:       { bg: 'bg-green-500/20',  text: 'text-green-400',  dot: 'bg-green-500'  },
    transport:     { bg: 'bg-yellow-500/20', text: 'text-yellow-400', dot: 'bg-yellow-500' },
    entertainment: { bg: 'bg-purple-500/20', text: 'text-purple-400', dot: 'bg-purple-500' },
    utilities:     { bg: 'bg-gray-500/20',   text: 'text-gray-400',   dot: 'bg-gray-500'   },
    rent:          { bg: 'bg-indigo-500/20', text: 'text-indigo-400', dot: 'bg-indigo-500' },
    healthcare:    { bg: 'bg-pink-500/20',   text: 'text-pink-400',   dot: 'bg-pink-500'   },
    education:     { bg: 'bg-teal-500/20',   text: 'text-teal-400',   dot: 'bg-teal-500'   },
    transfers:     { bg: 'bg-orange-500/20', text: 'text-orange-400', dot: 'bg-orange-500' },
    investments:   { bg: 'bg-cyan-500/20',   text: 'text-cyan-400',   dot: 'bg-cyan-500'   },
    uncategorized: { bg: 'bg-slate-500/20',  text: 'text-slate-400',  dot: 'bg-slate-500'  },
  }
  return map[category?.toLowerCase()] || map.uncategorized
}

// ── Hex colors: named categories ─────────────────────────────────────────────
export const CATEGORY_HEX = {
  // Core categories
  Food:             '#ef4444',
  Shopping:         '#3b82f6',
  Grocery:          '#22c55e',
  Transport:        '#eab308',
  Entertainment:    '#a855f7',
  Utilities:        '#6b7280',
  Rent:             '#6366f1',
  Healthcare:       '#ec4899',
  Education:        '#14b8a6',
  Transfers:        '#f97316',
  Investments:      '#06b6d4',
  Miscellaneous:    '#f43f5e',
  miscellaneous:    '#f43f5e',
  // Common merchant-based categories
  Amazon:           '#ff9900',
  Flipkart:         '#457ebb',
  Zomato:           '#e23744',
  Swiggy:           '#fc8019',
  Uber:             '#000000',
  Ola:              '#1dbe5a',
  Netflix:          '#e50914',
  Hotstar:          '#1f80e0',
  Spotify:          '#1db954',
  Paytm:            '#002970',
  PhonePe:          '#5f259f',
  'Big Basket':     '#84cc16',
  BigBasket:        '#84cc16',
  Recharge:         '#0ea5e9',
  Travel:           '#8b5cf6',
  Bills:            '#64748b',
  Insurance:        '#059669',
  'EMI':            '#dc2626',
  Salary:           '#16a34a',
  Refund:           '#0284c7',
  // Uncategorized fallback
  Uncategorized:    '#94a3b8',
}

// ── Dynamic color palette for any category not in CATEGORY_HEX ───────────────
// Vibrant, distinct colors that look great on dark backgrounds
const _DYNAMIC_PALETTE = [
  '#f97316', '#06b6d4', '#84cc16', '#ec4899', '#8b5cf6',
  '#14b8a6', '#f59e0b', '#ef4444', '#3b82f6', '#a855f7',
  '#10b981', '#f43f5e', '#6366f1', '#0ea5e9', '#d946ef',
  '#22c55e', '#eab308', '#64748b', '#c084fc', '#fb923c',
]
const _dynamicCache = new Map()
let   _dynamicIdx   = 0

/**
 * Returns a hex color for any category name.
 * Known categories get their defined color.
 * Unknown categories cycle through a vibrant dynamic palette.
 */
export function getCategoryHex(category) {
  if (!category) return CATEGORY_HEX.Uncategorized

  // Direct match first (case-sensitive defined categories)
  if (CATEGORY_HEX[category]) return CATEGORY_HEX[category]

  // Case-insensitive match against known categories
  const lower = category.toLowerCase()
  for (const [key, color] of Object.entries(CATEGORY_HEX)) {
    if (key.toLowerCase() === lower) return color
  }

  // Dynamic assignment — stable per session (same category always same color)
  if (!_dynamicCache.has(lower)) {
    _dynamicCache.set(lower, _DYNAMIC_PALETTE[_dynamicIdx % _DYNAMIC_PALETTE.length])
    _dynamicIdx++
  }
  return _dynamicCache.get(lower)
}

/** Compact number: 125000 → "1.25L" */
export function compactNumber(n) {
  if (n >= 10_000_000) return `${(n / 10_000_000).toFixed(1)}Cr`
  if (n >= 100_000)    return `${(n / 100_000).toFixed(1)}L`
  if (n >= 1000)       return `${(n / 1000).toFixed(1)}K`
  return String(n)
}
