'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BellPlus, Check, Loader2 } from 'lucide-react'
import { API_URL } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { track } from '@/lib/analytics'

interface RequestState {
  requests: number
  requested: boolean
}

// Shown where a case has no brief yet. Requests feed a demand-ordered queue that
// the brief writers work through; there is no live generation for readers.
export default function RequestBrief({ caseId }: { caseId: string }) {
  const { user, session } = useAuth()
  const pathname = usePathname()
  const [state, setState] = useState<RequestState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const token = session?.access_token

  useEffect(() => {
    let cancelled = false
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    fetch(`${API_URL}/api/v1/cases/${caseId}/brief-request`, { headers })
      .then(res => (res.ok ? res.json() : null))
      .then(data => { if (!cancelled && data) setState(data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [caseId, token])

  const request = async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/cases/${caseId}/brief-request`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Couldn’t save your request. Try again in a moment.')
      setState(data)
      track('brief_request', { case_id: caseId })
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const others = state ? state.requests - (state.requested ? 1 : 0) : 0

  return (
    <div className="space-y-2">
      <p className="font-medium text-ink">Brief coming soon</p>
      <p className="text-sm text-stone-600">
        We write and fact-check every brief against the opinion before it goes up.
        Request this one and we&apos;ll move it up the list.
      </p>
      {state?.requested ? (
        <p className="inline-flex items-center gap-1.5 text-sm font-medium text-sage-700">
          <Check className="h-4 w-4" />
          Requested{others > 0 ? ` (along with ${others} other reader${others === 1 ? '' : 's'})` : ''}
        </p>
      ) : !user ? (
        <Link
          href={`/login?returnTo=${encodeURIComponent(pathname)}`}
          className="inline-flex items-center rounded-lg bg-sage-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-sage-800"
        >
          <BellPlus className="mr-2 h-4 w-4" />
          Sign in to request this brief
        </Link>
      ) : (
        <button
          type="button"
          onClick={request}
          disabled={loading}
          className="inline-flex items-center rounded-lg bg-sage-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-sage-800 disabled:bg-neutral-400"
        >
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BellPlus className="mr-2 h-4 w-4" />}
          Request this brief
        </button>
      )}
      {!state?.requested && state && state.requests > 0 && (
        <p className="text-xs text-stone-500">
          {state.requests} reader{state.requests === 1 ? ' has' : 's have'} asked for this one.
        </p>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
