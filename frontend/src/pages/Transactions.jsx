import React, { useEffect, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Search, X, Pencil, Trash2, ChevronLeft, ChevronRight,
  ArrowDownLeft, ArrowUpRight, FileText,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Card from '../components/common/Card.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import Button from '../components/common/Button.jsx'
import ModalPortal from '../components/common/ModalPortal.jsx'
import api from '../services/api.js'
import { formatCurrency, formatDate } from '../utils/formatters.js'

const BANKS     = ['sbi', 'hdfc', 'icici', 'bob', 'idbi', 'kotak', 'cbi']
const PAGE_SIZE = 50

const BANK_LABELS = {
  sbi: 'SBI', hdfc: 'HDFC', icici: 'ICICI', bob: 'BOB',
  idbi: 'IDBI', kotak: 'Kotak', cbi: 'CBI',
}

// ── Edit modal ────────────────────────────────────────────────────────────────
function EditModal({ txn, onClose, onSaved }) {
  const [form, setForm] = useState({
    merchant: txn.merchant || '',
    category: txn.category || 'Uncategorized',
    amount:   txn.amount || 0,
    type:     txn.type || 'debit',
  })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.transactions.update(txn.id, form)
      toast.success('Transaction updated')
      onSaved()
      onClose()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  return (
    <ModalPortal onClose={onClose}>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
        <div className="w-full max-w-md rounded-2xl border border-white/[0.1]
                        bg-[#13152a] shadow-[0_24px_80px_rgba(0,0,0,0.7)] animate-fade-in">
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
            <h3 className="font-semibold text-white">Edit Transaction</h3>
            <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="p-6 space-y-4">
            <div>
              <label className="label">Merchant</label>
              <input className="input" value={form.merchant}
                onChange={(e) => setForm({ ...form, merchant: e.target.value })} />
            </div>
            <div>
              <label className="label">Category</label>
              <input className="input" value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Amount (₹)</label>
                <input type="number" min="0" step="0.01" className="input" value={form.amount}
                  onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })} />
              </div>
              <div>
                <label className="label">Type</label>
                <select className="input" value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  <option value="debit">Debit</option>
                  <option value="credit">Credit</option>
                </select>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-white/[0.06]">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button loading={saving} onClick={handleSave}>Save changes</Button>
          </div>
        </div>
      </div>
    </ModalPortal>
  )
}

// ── Delete confirm modal ──────────────────────────────────────────────────────
function DeleteModal({ txn, onClose, onDeleted }) {
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await api.transactions.delete(txn.id)
      toast.success('Transaction deleted')
      onDeleted()
      onClose()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  return (
    <ModalPortal onClose={onClose}>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
        <div className="w-full max-w-sm rounded-2xl border border-white/[0.1]
                        bg-[#13152a] shadow-[0_24px_80px_rgba(0,0,0,0.7)] p-6 text-center animate-fade-in">
          <div className="w-12 h-12 rounded-full bg-red-500/15 border border-red-500/20
                          flex items-center justify-center mx-auto mb-4">
            <Trash2 className="w-6 h-6 text-red-400" />
          </div>
          <h3 className="font-semibold text-white mb-1">Delete transaction?</h3>
          <p className="text-sm text-gray-400 mb-6">
            {txn.merchant} · {formatCurrency(txn.amount)}. This cannot be undone.
          </p>
          <div className="flex gap-3">
            <Button variant="secondary" className="flex-1" onClick={onClose}>Cancel</Button>
            <Button variant="danger" className="flex-1" loading={deleting} onClick={handleDelete}>Delete</Button>
          </div>
        </div>
      </div>
    </ModalPortal>
  )
}

// ── Category badge ────────────────────────────────────────────────────────────
function CategoryBadge({ category }) {
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold
                     bg-white/[0.06] border border-white/[0.1] text-gray-300">
      {category || 'Other'}
    </span>
  )
}

// ── Type badge ────────────────────────────────────────────────────────────────
function TypeBadge({ type }) {
  const isCredit = type === 'credit'
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold
      ${isCredit
        ? 'bg-emerald-500/10 border border-emerald-500/25 text-emerald-400'
        : 'bg-red-500/10 border border-red-500/25 text-red-400'}`}>
      {isCredit
        ? <ArrowDownLeft className="w-3 h-3" />
        : <ArrowUpRight className="w-3 h-3" />}
      {isCredit ? 'Credit' : 'Debit'}
    </span>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Transactions() {
  const [searchParams] = useSearchParams()
  const [txns, setTxns]         = useState([])
  const [total, setTotal]        = useState(0)
  const [page, setPage]          = useState(1)
  const [loading, setLoading]    = useState(true)
  const [error, setError]        = useState(null)
  const [search, setSearch]      = useState(searchParams.get('merchant') || '')
  const [bankFilter, setBankFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [dateFrom, setDateFrom]  = useState('')
  const [dateTo, setDateTo]      = useState('')
  const [editTxn, setEditTxn]    = useState(null)
  const [deleteTxn, setDeleteTxn] = useState(null)
  const searchTimer = useRef(null)

  const fetchTxns = useCallback(async (pg = 1) => {
    setLoading(true)
    setError(null)
    try {
      const filters = { page: pg, page_size: PAGE_SIZE }
      if (bankFilter) filters.bank      = bankFilter
      if (typeFilter) filters.type      = typeFilter
      if (dateFrom)   filters.date_from = dateFrom
      if (dateTo)     filters.date_to   = dateTo
      const res = await api.transactions.getAll(filters)
      let data = res.data || []
      if (search) {
        const q = search.toLowerCase()
        data = data.filter(
          (t) => t.merchant?.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q)
        )
      }
      setTxns(data)
      setTotal(res.total || data.length)
      setPage(pg)
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load transactions')
    } finally {
      setLoading(false)
    }
  }, [bankFilter, typeFilter, dateFrom, dateTo, search])

  useEffect(() => { fetchTxns(1) }, [bankFilter, typeFilter, dateFrom, dateTo])
  useEffect(() => {
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => fetchTxns(1), 300)
    return () => clearTimeout(searchTimer.current)
  }, [search])

  const totalPages = Math.ceil(total / PAGE_SIZE)
  const hasFilters = search || bankFilter || typeFilter || dateFrom || dateTo

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Page heading */}
      <div>
        <h1 className="text-2xl font-bold text-white">Transactions</h1>
        <p className="text-gray-400 text-sm mt-0.5">{total} total records</p>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              className="input pl-9"
              placeholder="Search merchant or description…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {/* Bank */}
          <select className="input w-auto min-w-[110px]" value={bankFilter} onChange={(e) => setBankFilter(e.target.value)}>
            <option value="">All Banks</option>
            {BANKS.map((b) => <option key={b} value={b}>{BANK_LABELS[b] || b.toUpperCase()}</option>)}
          </select>
          {/* Type */}
          <select className="input w-auto" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">All Types</option>
            <option value="debit">Debit</option>
            <option value="credit">Credit</option>
          </select>
          {/* Date range */}
          <input type="date" className="input w-auto" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} title="From date" />
          <input type="date" className="input w-auto" value={dateTo}   onChange={(e) => setDateTo(e.target.value)}   title="To date"   />
          {hasFilters && (
            <Button variant="secondary" onClick={() => {
              setSearch(''); setBankFilter(''); setTypeFilter(''); setDateFrom(''); setDateTo('')
            }}>
              <X className="w-4 h-4" /> Clear
            </Button>
          )}
        </div>
      </Card>

      {/* Table */}
      <Card className="p-0 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <LoadingSpinner size="lg" />
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <p className="text-red-400 text-sm">{error}</p>
            <Button variant="secondary" className="mt-3" onClick={() => fetchTxns(page)}>Retry</Button>
          </div>
        ) : txns.length === 0 ? (
          <div className="py-20 text-center">
            <FileText className="w-10 h-10 mx-auto mb-3 text-gray-600" />
            <p className="text-gray-400 text-sm">No transactions found.</p>
            <p className="text-gray-600 text-xs mt-1">Try adjusting your filters or upload a statement.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  {['Date','Merchant','Category','Amount','Type','Bank','Actions'].map((h, i) => (
                    <th key={h} className={`px-5 py-3.5 text-[11px] font-bold text-gray-500 uppercase tracking-widest
                      ${i === 3 ? 'text-right' : i === 6 ? 'text-center' : 'text-left'}`}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {txns.map((t) => (
                  <tr key={t.id}
                    className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors group">
                    {/* Date */}
                    <td className="px-5 py-3.5 text-gray-400 whitespace-nowrap text-sm">
                      {formatDate(t.date)}
                    </td>
                    {/* Merchant */}
                    <td className="px-5 py-3.5 max-w-[200px]">
                      <p className="font-semibold text-gray-100 truncate">{t.merchant || '—'}</p>
                      <p className="text-[11px] text-gray-600 truncate mt-0.5">{t.description}</p>
                    </td>
                    {/* Category */}
                    <td className="px-5 py-3.5">
                      <CategoryBadge category={t.category} />
                    </td>
                    {/* Amount */}
                    <td className="px-5 py-3.5 text-right">
                      <span className={`font-bold text-base ${t.type === 'credit' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {t.type === 'debit' ? '−' : '+'}{formatCurrency(t.amount)}
                      </span>
                    </td>
                    {/* Type */}
                    <td className="px-5 py-3.5">
                      <TypeBadge type={t.type} />
                    </td>
                    {/* Bank */}
                    <td className="px-5 py-3.5">
                      <span className="px-2 py-0.5 rounded-md bg-white/[0.05] border border-white/[0.08]
                                       text-xs font-bold text-gray-400 uppercase">
                        {BANK_LABELS[t.bank] || t.bank}
                      </span>
                    </td>
                    {/* Actions */}
                    <td className="px-5 py-3.5">
                      <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setEditTxn(t)}
                          className="p-1.5 rounded-lg text-gray-500 hover:text-violet-400 hover:bg-violet-500/10 transition-all"
                          aria-label="Edit">
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setDeleteTxn(t)}
                          className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                          aria-label="Delete">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && !error && totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3.5 border-t border-white/[0.06]">
            <p className="text-xs text-gray-500">
              Page <span className="text-gray-300 font-medium">{page}</span> of {totalPages} · {total} records
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => fetchTxns(page - 1)}
                disabled={page === 1}
                className="p-1.5 rounded-lg disabled:opacity-30 text-gray-400 hover:text-white
                           hover:bg-white/[0.06] transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                const n = page <= 3 ? i + 1 : page - 2 + i
                if (n < 1 || n > totalPages) return null
                return (
                  <button key={n} onClick={() => fetchTxns(n)}
                    className={`w-8 h-8 text-xs rounded-lg font-semibold transition-all ${
                      n === page
                        ? 'bg-violet-600 text-white shadow-[0_0_12px_rgba(109,40,217,0.5)]'
                        : 'text-gray-400 hover:text-white hover:bg-white/[0.06]'
                    }`}>
                    {n}
                  </button>
                )
              })}
              <button
                onClick={() => fetchTxns(page + 1)}
                disabled={page === totalPages}
                className="p-1.5 rounded-lg disabled:opacity-30 text-gray-400 hover:text-white
                           hover:bg-white/[0.06] transition-colors">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </Card>

      {/* Modals */}
      {editTxn   && <EditModal   txn={editTxn}   onClose={() => setEditTxn(null)}   onSaved={() => fetchTxns(page)} />}
      {deleteTxn && <DeleteModal txn={deleteTxn} onClose={() => setDeleteTxn(null)} onDeleted={() => fetchTxns(page)} />}
    </div>
  )
}
