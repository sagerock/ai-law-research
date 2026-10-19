'use client'

import { useEffect, useState } from 'react'
import { API_URL } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

export interface AiAccess {
  live_ai: boolean
  is_admin: boolean
  is_byok: boolean
}

const NO_ACCESS: AiAccess = { live_ai: false, is_admin: false, is_byok: false }

// Live AI generation is admin-only, or the reader's own key (Sage, 2026-10-19).
// Everyone else reads briefs written ahead of time and can request missing ones.
export function useAiAccess(): AiAccess {
  const { session } = useAuth()
  const [access, setAccess] = useState<AiAccess>(NO_ACCESS)
  const token = session?.access_token

  useEffect(() => {
    if (!token) {
      setAccess(NO_ACCESS)
      return
    }
    let cancelled = false
    fetch(`${API_URL}/api/v1/me/ai-access`, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => (res.ok ? res.json() : NO_ACCESS))
      .then(data => { if (!cancelled) setAccess({ ...NO_ACCESS, ...data }) })
      .catch(() => { if (!cancelled) setAccess(NO_ACCESS) })
    return () => { cancelled = true }
  }, [token])

  return access
}
