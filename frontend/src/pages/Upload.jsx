import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import {
  UploadCloud, FileText, X, CheckCircle2, AlertCircle, Lock, Building2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Card from '../components/common/Card.jsx'
import Button from '../components/common/Button.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import api from '../services/api.js'
import { formatCurrency } from '../utils/formatters.js'
import { addUploadNotification } from '../components/common/NotificationDropdown.jsx'

const BANKS = [
  { value: '',       label: 'Auto-detect'         },
  { value: 'sbi',   label: 'State Bank of India'  },
  { value: 'hdfc',  label: 'HDFC Bank'            },
  { value: 'icici', label: 'ICICI Bank'           },
  { value: 'bob',   label: 'Bank of Baroda'       },
  { value: 'idbi',  label: 'IDBI Bank'            },
  { value: 'kotak', label: 'Kotak Mahindra Bank'  },
  { value: 'cbi',   label: 'Central Bank of India'},
]

export default function Upload() {
  const navigate  = useNavigate()
  const [file, setFile]               = useState(null)
  const [password, setPassword]       = useState('')
  const [bank, setBank]               = useState('')
  const [progress, setProgress]       = useState(0)
  const [uploading, setUploading]     = useState(false)
  const [result, setResult]           = useState(null)  // UploadResult
  const [uploadError, setUploadError] = useState(null)

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected.length > 0) {
      toast.error(rejected[0].errors[0]?.message || 'Invalid file')
      return
    }
    if (accepted.length > 0) {
      setFile(accepted[0])
      setResult(null)
      setUploadError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 10 * 1024 * 1024,  // 10 MB
    multiple: false,
  })

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setProgress(0)
    setUploadError(null)
    setResult(null)
    try {
      const res = await api.upload.statement(file, password || null, bank || null, (pct) => setProgress(pct))
      setResult(res)
      toast.success(`Imported ${res.inserted} transactions!`)
      // Store notification for the bell icon
      addUploadNotification(res.bank || bank || 'bank', res.inserted)
      // auto-navigate after 3s
      setTimeout(() => navigate('/transactions'), 3000)
    } catch (e) {
      const detail = e.response?.data?.detail || 'Upload failed. Check the file and try again.'
      setUploadError(detail)
      toast.error(detail)
    } finally {
      setUploading(false)
    }
  }

  const clearFile = () => {
    setFile(null)
    setResult(null)
    setUploadError(null)
    setProgress(0)
  }

  return (
    <div className="space-y-6 max-w-2xl animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Upload Statement</h1>
        <p className="text-gray-400 text-sm mt-0.5">Import your bank PDF and we'll extract &amp; categorize every transaction.</p>
      </div>

      {/* Instructions */}
      <Card className="bg-violet-500/5 border-violet-500/20">
        <div className="flex gap-3">
          <Building2 className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-violet-300 mb-2">Supported Banks</p>
            <div className="flex flex-wrap gap-1.5">
              {['SBI','HDFC','ICICI','Bank of Baroda','IDBI','Kotak','Central Bank'].map(b => (
                <span key={b} className="px-2 py-0.5 rounded-md bg-white/[0.06] border border-white/[0.08] text-xs text-gray-400 font-medium">{b}</span>
              ))}
            </div>
            <p className="text-xs text-gray-600 mt-2">Only text-based PDFs are supported (not scanned images).</p>
          </div>
        </div>
      </Card>

      {/* Drop zone */}
      <Card>
        {!result ? (
          <>
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all
                ${isDragActive
                  ? 'border-violet-400 bg-violet-500/10'
                  : 'border-white/[0.12] hover:border-violet-500/50 hover:bg-violet-500/5'
                }
              `}
            >
              <input {...getInputProps()} />
              <UploadCloud className={`w-10 h-10 mx-auto mb-3 ${isDragActive ? 'text-violet-400' : 'text-gray-600'}`} />
              {file ? (
                <div className="flex items-center justify-center gap-2 text-sm text-gray-300">
                  <FileText className="w-4 h-4 text-violet-400" />
                  <span className="font-medium truncate max-w-xs text-white">{file.name}</span>
                  <span className="text-gray-500">({(file.size / 1024).toFixed(0)} KB)</span>
                </div>
              ) : (
                <>
                  <p className="text-sm font-medium text-gray-400">
                    {isDragActive ? 'Drop it here!' : 'Drag & drop your PDF, or click to browse'}
                  </p>
                  <p className="text-xs text-gray-600 mt-1">PDF only · max 10 MB</p>
                </>
              )}
            </div>

            {file && (
              <div className="mt-4 space-y-3">
                {/* Options row */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Bank selector */}
                  <div>
                    <label className="label">Bank (optional)</label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <select className="input pl-9" value={bank} onChange={(e) => setBank(e.target.value)}>
                        {BANKS.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
                      </select>
                    </div>
                  </div>
                  {/* Password */}
                  <div>
                    <label className="label">PDF Password (if protected)</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="password"
                        className="input pl-9"
                        placeholder="e.g. DDMMYYYY"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                {/* Progress */}
                {uploading && (
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Uploading…</span><span>{progress}%</span>
                    </div>
                    <div className="w-full bg-white/[0.06] rounded-full h-1.5">
                      <div
                        className="bg-violet-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Error */}
                {uploadError && (
                  <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    {uploadError}
                  </div>
                )}

                {/* Buttons */}
                <div className="flex gap-3 pt-1">
                  <Button variant="secondary" onClick={clearFile} disabled={uploading}>
                    <X className="w-4 h-4" /> Remove
                  </Button>
                  <Button onClick={handleUpload} loading={uploading} disabled={!file}>
                    <UploadCloud className="w-4 h-4" />
                    {uploading ? 'Uploading…' : 'Upload Statement'}
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Success state */
          <div className="py-8 text-center">
            <div className="w-14 h-14 rounded-full bg-emerald-500/15 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-7 h-7 text-emerald-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-1">Upload Successful!</h3>
            <p className="text-gray-400 text-sm mb-5">
              Bank: <span className="font-semibold text-violet-400 uppercase">{result.bank}</span>
            </p>
            {/* Stats grid */}
            <div className="grid grid-cols-3 gap-4 max-w-xs mx-auto mb-6">
              {[
                { label: 'Total rows',  value: result.total_rows  },
                { label: 'Inserted',    value: result.inserted    },
                { label: 'Duplicates',  value: result.duplicates  },
              ].map(({ label, value }) => (
                <div key={label} className="bg-white/[0.05] border border-white/[0.08] rounded-xl p-3">
                  <p className="text-xl font-bold text-white">{value}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{label}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-600">Redirecting to transactions in 3s…</p>
            <Button className="mt-4" onClick={() => navigate('/transactions')}>View Transactions →</Button>
          </div>
        )}
      </Card>
    </div>
  )
}
