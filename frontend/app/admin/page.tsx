'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Scale, Shield, Search, Check, Loader2 } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { UserMenu } from '@/components/auth/UserMenu'
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

  useEffect(() => {
    if (user?.email === ADMIN_EMAIL && session?.access_token) {
      fetchUsers()
    }
  }, [user, session?.access_token, tierFilter, fetchUsers])

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
      {/* Header */}
      <header className="bg-white border-b border-stone-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2.5 group">
                <div className="w-8 h-8 bg-sage-700 rounded-xl flex items-center justify-center group-hover:bg-sage-600 transition-colors">
                  <Scale className="h-[16px] w-[16px] text-white" />
                </div>
                <span className="font-display text-lg text-stone-900">Law Study Group</span>
              </Link>
              <div className="flex items-center gap-2 px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-sm font-medium">
                <Shield className="h-4 w-4" />
                Admin Panel
              </div>
            </div>
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
