'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Shield, Search, Check, Loader2, Plus, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import Header from '@/components/Header'
import type { AdminUser } from '@/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const ADMIN_EMAIL = 'sage@sagerock.com'

const MODEL_OPTIONS = [
  { value: '', label: 'Default (tier-based)' },
  { value: 'claude-haiku-4-5-20251001', label: 'Haiku' },
  { value: 'claude-sonnet-4-5-20250929', label: 'Sonnet' },
]

export default function AdminPage() {
  const router = useRouter()
  const { user, session, isLoading: authLoading } = useAuth()

  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [tierFilter, setTierFilter] = useState('')
  const [editState, setEditState] = useState<Record<string, { tier?: string; daily_limit?: string; model_override?: string }>>({})
  const [savingId, setSavingId] = useState<string | null>(null)
  const [savedId, setSavedId] = useState<string | null>(null)

  // Pool state
  const [poolData, setPoolData] = useState<{
    balance: number
    low_threshold: number
    is_low: boolean
    recent_entries: Array<{
      id: number
      amount: number
      entry_type: string
      description: string | null
      created_at: string | null
    }>
  } | null>(null)
  const [poolLoading, setPoolLoading] = useState(true)
  const [addAmount, setAddAmount] = useState('')
  const [addDescription, setAddDescription] = useState('')
  const [addingFunds, setAddingFunds] = useState(false)
  const [showLedger, setShowLedger] = useState(false)

  const getAuthHeaders = useCallback((): Record<string, string> => {
    if (!session?.access_token) return {}
    return {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json',
    }
  }, [session?.access_token])

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    } else if (!authLoading && user && user.email !== ADMIN_EMAIL) {
      router.push('/')
    }
  }, [authLoading, user, router])

  const fetchUsers = useCallback(async () => {
    if (!session?.access_token) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (tierFilter) params.set('tier_filter', tierFilter)
      const res = await fetch(`${API_URL}/api/v1/admin/users?${params}`, {
        headers: getAuthHeaders(),
      })
      if (res.ok) {
        const data = await res.json()
        setUsers(data)
      }
    } catch (e) {
      console.error('Failed to fetch users:', e)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, search, tierFilter, getAuthHeaders])

  const fetchPool = useCallback(async () => {
    if (!session?.access_token) return
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/pool`, {
        headers: getAuthHeaders(),
      })
      if (res.ok) setPoolData(await res.json())
    } catch (e) {
      console.error('Failed to fetch pool:', e)
    } finally {
      setPoolLoading(false)
    }
  }, [session?.access_token, getAuthHeaders])

  const addFunds = async () => {
    const amt = parseFloat(addAmount)
    if (!amt || amt <= 0) return
    setAddingFunds(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/admin/pool/add`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ amount: amt, description: addDescription || undefined }),
      })
      if (res.ok) {
        setAddAmount('')
        setAddDescription('')
        fetchPool()
      }
    } catch (e) {
      console.error('Failed to add funds:', e)
    } finally {
      setAddingFunds(false)
    }
  }

  useEffect(() => {
    if (user?.email === ADMIN_EMAIL && session?.access_token) {
      fetchUsers()
      fetchPool()
    }
  }, [user, session?.access_token, tierFilter, fetchUsers, fetchPool])

  // Debounced search
  useEffect(() => {
    if (!user || user.email !== ADMIN_EMAIL) return
    const timer = setTimeout(() => fetchUsers(), 300)
    return () => clearTimeout(timer)
  }, [search])

  const getEdit = (userId: string) => editState[userId] || {}

  const updateEdit = (userId: string, field: string, value: string) => {
    setEditState(prev => ({
      ...prev,
      [userId]: { ...prev[userId], [field]: value },
    }))
  }

  const saveUser = async (u: AdminUser) => {
    const edit = getEdit(u.id)
    if (!Object.keys(edit).length) return

    setSavingId(u.id)
    try {
      const body: Record<string, unknown> = {}

      if (edit.tier !== undefined && edit.tier !== u.tier) {
        body.tier = edit.tier
      }
      if (edit.daily_limit !== undefined) {
        const val = edit.daily_limit.trim()
        if (val === '') {
          body.daily_limit = -1  // clear override
        } else {
          body.daily_limit = parseInt(val, 10)
        }
      }
      if (edit.model_override !== undefined) {
        body.model_override = edit.model_override  // "" clears it
      }

      if (!Object.keys(body).length) {
        setSavingId(null)
        return
      }

      const res = await fetch(`${API_URL}/api/v1/admin/users/${u.id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      })

      if (res.ok) {
        const updated = await res.json()
        setUsers(prev => prev.map(x => x.id === u.id ? { ...x, ...updated } : x))
        setEditState(prev => {
          const next = { ...prev }
          delete next[u.id]
          return next
        })
        setSavedId(u.id)
        setTimeout(() => setSavedId(null), 2000)
      }
    } catch (e) {
      console.error('Failed to update user:', e)
    } finally {
      setSavingId(null)
    }
  }

  if (authLoading || !user || user.email !== ADMIN_EMAIL) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-sage-600" />
      </div>
    )
  }

  const modelLabel = (model: string) => {
    if (model.includes('haiku')) return 'Haiku'
    if (model.includes('sonnet')) return 'Sonnet'
    return model
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Community Pool */}
        <div className="bg-white rounded-lg border border-stone-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-stone-900 mb-4 flex items-center">
            <Zap className="h-5 w-5 mr-2 text-amber-500" />
            Community AI Pool
          </h2>

          {poolLoading ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
            </div>
          ) : poolData && (
            <div className="space-y-4">
              {/* Balance */}
              <div className="flex items-center gap-4">
                <div className={`text-4xl font-bold ${
                  poolData.balance <= 0 ? 'text-red-500' :
                  poolData.is_low ? 'text-amber-500' :
                  'text-green-600'
                }`}>
                  ${poolData.balance.toFixed(2)}
                </div>
                <div className="text-sm text-stone-500">
                  {poolData.balance <= 0 ? 'Pool empty — free AI paused' :
                   poolData.is_low ? `Low balance (threshold: $${poolData.low_threshold})` :
                   'Pool healthy'}
                </div>
              </div>

              {/* Add Funds */}
              <div className="flex items-end gap-3">
                <div>
                  <label className="block text-xs font-medium text-stone-500 mb-1">Amount ($)</label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={addAmount}
                    onChange={e => setAddAmount(e.target.value)}
                    placeholder="50.00"
                    className="w-28 px-3 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-200"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-stone-500 mb-1">Description (optional)</label>
                  <input
                    type="text"
                    value={addDescription}
                    onChange={e => setAddDescription(e.target.value)}
                    placeholder="Initial pool funding"
                    className="w-full px-3 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-200"
                  />
                </div>
                <button
                  onClick={addFunds}
                  disabled={addingFunds || !addAmount || parseFloat(addAmount) <= 0}
                  className="flex items-center px-4 py-2 bg-sage-700 hover:bg-sage-600 text-white rounded-lg text-sm font-medium disabled:bg-stone-300 disabled:cursor-not-allowed transition"
                >
                  {addingFunds ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-1" />
                      Add Funds
                    </>
                  )}
                </button>
              </div>

              {/* Ledger toggle */}
              <button
                onClick={() => setShowLedger(!showLedger)}
                className="flex items-center text-sm text-stone-500 hover:text-stone-700 transition"
              >
                {showLedger ? <ChevronUp className="h-4 w-4 mr-1" /> : <ChevronDown className="h-4 w-4 mr-1" />}
                {showLedger ? 'Hide' : 'Show'} recent ledger entries
              </button>

              {/* Ledger entries */}
              {showLedger && poolData.recent_entries.length > 0 && (
                <div className="border border-stone-200 rounded-lg overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-stone-50 border-b border-stone-200">
                        <th className="text-left px-3 py-2 font-medium text-stone-600">Date</th>
                        <th className="text-left px-3 py-2 font-medium text-stone-600">Type</th>
                        <th className="text-right px-3 py-2 font-medium text-stone-600">Amount</th>
                        <th className="text-left px-3 py-2 font-medium text-stone-600">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {poolData.recent_entries.slice(0, 20).map(e => (
                        <tr key={e.id} className="border-b border-stone-100">
                          <td className="px-3 py-1.5 text-stone-400">
                            {e.created_at ? new Date(e.created_at).toLocaleDateString() : '-'}
                          </td>
                          <td className="px-3 py-1.5">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                              e.entry_type === 'ai_debit' ? 'bg-red-50 text-red-700' :
                              e.entry_type === 'donation' ? 'bg-green-50 text-green-700' :
                              'bg-blue-50 text-blue-700'
                            }`}>
                              {e.entry_type}
                            </span>
                          </td>
                          <td className={`px-3 py-1.5 text-right font-mono ${e.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {e.amount < 0 ? '-' : '+'}${Math.abs(e.amount).toFixed(4)}
                          </td>
                          <td className="px-3 py-1.5 text-stone-600">{e.description || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400" />
            <input
              type="text"
              placeholder="Search by email, username, or name..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-200"
            />
          </div>
          <select
            value={tierFilter}
            onChange={e => setTierFilter(e.target.value)}
            className="px-3 py-2 border border-stone-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-sage-200"
          >
            <option value="">All tiers</option>
            <option value="free">Free</option>
            <option value="pro">Pro</option>
          </select>
        </div>

        {/* User count */}
        <p className="text-sm text-stone-500 mb-4">
          {users.length} user{users.length !== 1 ? 's' : ''}
          {loading && <Loader2 className="inline h-3 w-3 ml-2 animate-spin" />}
        </p>

        {/* Table */}
        <div className="bg-white rounded-lg border border-stone-200 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 bg-stone-50">
                <th className="text-left px-4 py-3 font-medium text-stone-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-stone-600">Username</th>
                <th className="text-left px-4 py-3 font-medium text-stone-600">Tier</th>
                <th className="text-left px-4 py-3 font-medium text-stone-600">Msgs Today</th>
                <th className="text-left px-4 py-3 font-medium text-stone-600">Daily Limit</th>
                <th className="text-left px-4 py-3 font-medium text-stone-600">Model</th>
                <th className="text-left px-4 py-3 font-medium text-stone-600">Last Active</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => {
                const edit = getEdit(u.id)
                const hasEdits = Object.keys(edit).length > 0
                const currentTier = edit.tier ?? u.tier
                const currentLimit = edit.daily_limit ?? (u.custom_daily_limit !== null ? String(u.custom_daily_limit) : '')
                const currentModel = edit.model_override ?? (u.model_override || '')

                return (
                  <tr key={u.id} className="border-b border-stone-100 hover:bg-stone-50">
                    <td className="px-4 py-3 text-stone-900">{u.email || <span className="text-stone-400">-</span>}</td>
                    <td className="px-4 py-3 text-stone-600">{u.username || <span className="text-stone-400">-</span>}</td>
                    <td className="px-4 py-3">
                      <select
                        value={currentTier}
                        onChange={e => updateEdit(u.id, 'tier', e.target.value)}
                        className={`px-2 py-1 rounded text-xs font-medium border ${
                          currentTier === 'pro'
                            ? 'bg-sage-50 text-sage-700 border-sage-200'
                            : 'bg-stone-50 text-stone-700 border-stone-200'
                        }`}
                      >
                        <option value="free">Free</option>
                        <option value="pro">Pro</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-stone-600">{u.messages_today}</td>
                    <td className="px-4 py-3">
                      <input
                        type="number"
                        min="0"
                        placeholder={currentTier === 'pro' ? '∞' : '15'}
                        value={currentLimit}
                        onChange={e => updateEdit(u.id, 'daily_limit', e.target.value)}
                        className="w-20 px-2 py-1 border border-stone-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-sage-200"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={currentModel}
                        onChange={e => updateEdit(u.id, 'model_override', e.target.value)}
                        className="px-2 py-1 border border-stone-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-sage-200"
                      >
                        {MODEL_OPTIONS.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-stone-400 text-xs">
                      {u.last_active
                        ? new Date(u.last_active).toLocaleDateString()
                        : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {savedId === u.id ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <button
                          onClick={() => saveUser(u)}
                          disabled={!hasEdits || savingId === u.id}
                          className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                            hasEdits
                              ? 'bg-sage-700 text-white hover:bg-sage-600'
                              : 'bg-stone-100 text-stone-400 cursor-not-allowed'
                          }`}
                        >
                          {savingId === u.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            'Save'
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-stone-400">
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
