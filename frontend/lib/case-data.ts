import type { CaseDetail } from '../app/case/[id]/CaseDetailClient'
import { API_URL } from './api'

export interface ResolveResult {
  case_id: string
  canonical_slug: string
}

export async function resolveSlug(slug: string): Promise<ResolveResult | null> {
  try {
    // no-store: crawlers sweep 50k+ unique case URLs, so Next's on-disk fetch cache
    // (never pruned) grew ~1.5 GB/day for no hit-rate benefit — see
    // ai-collab/2026-09-01-railway-memory-growth.md. Per-request memoization still
    // dedupes the generateMetadata + page calls. The backend answers resolve with
    // its own 24 h Cache-Control for anything in front of it.
    const response = await fetch(`${API_URL}/api/v1/cases/resolve/${slug}`, {
      cache: 'no-store',
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export async function getCase(id: string): Promise<CaseDetail | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/${id}`, {
      cache: 'no-store',
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export function caseYear(date?: string): string {
  if (!date) return ''
  const year = new Date(date).getUTCFullYear()
  return Number.isNaN(year) ? '' : String(year)
}
