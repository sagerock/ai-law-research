import { MetadataRoute } from 'next'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://lawstudygroup.com'

interface CaseForSitemap {
  id: string
  title: string
  date: string | null
  reporter_cite: string | null
  canonical_slug: string
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
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
  ]

  try {
    const response = await fetch(`${API_URL}/api/v1/sitemap/cases`, {
      next: { revalidate: 3600 }
    })

    if (!response.ok) {
      console.error('Failed to fetch cases for sitemap')
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
    console.error('Error generating sitemap:', error)
    return staticPages
  }
}
