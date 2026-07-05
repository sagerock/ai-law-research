import { MetadataRoute } from 'next'
import { CHUNK } from './sitemap'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://ai-law-research-production.up.railway.app'

export default async function robots(): Promise<MetadataRoute.Robots> {
  // with generateSitemaps, Next serves chunked files at /sitemap/[id].xml — list them all
  let sitemaps = [`${SITE_URL}/sitemap/0.xml`]
  try {
    const response = await fetch(`${API_URL}/api/v1/sitemap/count`, {
      next: { revalidate: 3600 },
    })
    if (response.ok) {
      const { count } = await response.json()
      const n = Math.max(1, Math.ceil(count / CHUNK))
      sitemaps = Array.from({ length: n }, (_, i) => `${SITE_URL}/sitemap/${i}.xml`)
    }
  } catch {
    // fall through with the single-chunk default
  }
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/auth/'],
    },
    sitemap: sitemaps,
  }
}
