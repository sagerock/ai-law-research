import { Metadata } from 'next'
import { notFound, redirect } from 'next/navigation'
import CaseDetailClient, { CaseDetail } from '../../case/[id]/CaseDetailClient'
import { BRAND_NAME, SITE_URL, SOCIAL_IMAGE } from '@/lib/site'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ResolveResult {
  case_id: string
  canonical_slug: string
}

interface PageProps {
  params: Promise<{ slug: string[] }>
}

async function resolveSlug(slug: string): Promise<ResolveResult | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/resolve/${slug}`, {
      next: { revalidate: 86400 } // Cache resolve for 24h — citations are immutable
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

async function getCase(id: string): Promise<CaseDetail | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/${id}`, {
      next: { revalidate: 3600 }
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const slugStr = slug.join('/')
  const resolved = await resolveSlug(slugStr)
  if (!resolved) return { title: 'Case Not Found' }

  const caseData = await getCase(resolved.case_id)
  if (!caseData) return { title: 'Case Not Found' }

  const caseName = caseData.title || caseData.case_name || 'Unknown Case'
  const court = caseData.court_name || ''
  const dateStr = caseData.decision_date || caseData.date_filed
  const year = dateStr ? new Date(dateStr).getFullYear() : ''
  const canonicalUrl = `${SITE_URL}/cases/${resolved.canonical_slug}`

  return {
    title: caseName,
    description: `Read the full case brief for ${caseName}${court ? ` (${court}${year ? `, ${year}` : ''})` : ''}. Free case briefs for law students.`,
    alternates: {
      canonical: canonicalUrl,
    },
    // Stub cases (no opinion text yet — e.g. citers pulled in from the citation graph)
    // are thin content until "graduated"; keep them out of the index until populated.
    ...(caseData.is_stub ? { robots: { index: false, follow: true } } : {}),
    openGraph: {
      title: `${caseName} | ${BRAND_NAME}`,
      description: `Case brief for ${caseName}`,
      type: 'article',
      url: canonicalUrl,
      images: [SOCIAL_IMAGE],
    },
  }
}

export default async function CitationCasePage({ params }: PageProps) {
  const { slug } = await params
  const slugStr = slug.join('/')

  const resolved = await resolveSlug(slugStr)
  if (!resolved) notFound()

  // Redirect to canonical slug if URL doesn't match
  if (slugStr !== resolved.canonical_slug) {
    redirect(`/cases/${resolved.canonical_slug}`)
  }

  const caseData = await getCase(resolved.case_id)
  if (!caseData) notFound()

  return <CaseDetailClient caseData={caseData} caseId={resolved.case_id} />
}
