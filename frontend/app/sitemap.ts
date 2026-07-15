import { MetadataRoute } from 'next'
import { SITE_URL } from '@/lib/site'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Sitemap protocol caps 50k URLs per file; the case count is past that, so we chunk.
// Chunks are served at /sitemap/[id].xml and listed in robots.ts.
export const CHUNK = 40000

interface CaseForSitemap {
  id: string
  title: string
  date: string | null
  reporter_cite: string | null
  canonical_slug: string
}

export async function generateSitemaps(): Promise<{ id: number }[]> {
  try {
    const response = await fetch(`${API_URL}/api/v1/sitemap/count`, {
      next: { revalidate: 3600 },
    })
    if (!response.ok) return [{ id: 0 }]
    const { count } = await response.json()
    const n = Math.max(1, Math.ceil(count / CHUNK))
    return Array.from({ length: n }, (_, id) => ({ id }))
  } catch {
    return [{ id: 0 }]
  }
}

export default async function sitemap({ id }: { id: Promise<string> }): Promise<MetadataRoute.Sitemap> {
  const sitemapId = Number(await id)
  // static pages ride along in the first chunk
  const staticPages: MetadataRoute.Sitemap = sitemapId === 0 ? [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${SITE_URL}/transparency`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/briefcheck`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${SITE_URL}/outlines/civil-procedure`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/outlines/torts`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.8,
    },
  ] : []

  try {
    const response = await fetch(
      `${API_URL}/api/v1/sitemap/cases?offset=${sitemapId * CHUNK}&limit=${CHUNK}`,
      { next: { revalidate: 3600 } }
    )

    if (!response.ok) {
      console.error('Failed to fetch cases for sitemap chunk', sitemapId)
      return staticPages
    }

    const data = await response.json()
    const cases: CaseForSitemap[] = data.cases || []

    const casePages: MetadataRoute.Sitemap = cases.map((c) => ({
      url: `${SITE_URL}/cases/${c.canonical_slug}`,
      lastModified: c.date ? new Date(c.date) : new Date(),
      changeFrequency: 'monthly' as const,
      priority: 0.6,
    }))

    return [...staticPages, ...casePages]
  } catch (error) {
    console.error('Error generating sitemap chunk', sitemapId, error)
    return staticPages
  }
}
