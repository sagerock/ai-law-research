import type { CaseDetail } from '../app/case/[id]/CaseDetailClient'
import { API_URL } from './api'

export interface ResolveResult {
  case_id: string
  canonical_slug: string
}

export async function resolveSlug(slug: string): Promise<ResolveResult | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/resolve/${slug}`, {
      next: { revalidate: 86400 },
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
      next: { revalidate: 3600 },
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
