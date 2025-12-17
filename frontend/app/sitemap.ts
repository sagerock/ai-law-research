import { MetadataRoute } from 'next'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://ai-law-research-production.up.railway.app'

interface CaseForSitemap {
  id: string
  title: string
  date: string | null
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Static pages
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

  // Fetch all cases from API
  try {
    const response = await fetch(`${API_URL}/api/v1/sitemap/cases`, {
      next: { revalidate: 3600 } // Revalidate every hour
    })

    if (!response.ok) {
      console.error('Failed to fetch cases for sitemap')
      return staticPages
    }

    const data = await response.json()
    const cases: CaseForSitemap[] = data.cases || []

    // Generate case page entries
    const casePages: MetadataRoute.Sitemap = cases.map((c) => ({
      url: `${SITE_URL}/case/${c.id}`,
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
