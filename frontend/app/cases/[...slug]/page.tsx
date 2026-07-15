import { Metadata } from 'next'
import { notFound, redirect } from 'next/navigation'
import CaseDetailClient from '../../case/[id]/CaseDetailClient'
import { BRAND_NAME, SITE_URL } from '@/lib/site'
import { caseYear, getCase, resolveSlug } from '@/lib/case-data'
import { getCaseArt } from '@/lib/caseArt'

interface PageProps {
  params: Promise<{ slug: string[] }>
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
  const year = caseYear(dateStr)
  const canonicalUrl = `${SITE_URL}/cases/${resolved.canonical_slug}`
  const art = getCaseArt(resolved.case_id)
  const socialImage = art
    ? { url: `${SITE_URL}${art.file}`, width: art.width, height: art.height, alt: art.alt }
    : {
        url: `${SITE_URL}/api/og/cases/${encodeURIComponent(resolved.case_id)}`,
        width: 1200,
        height: 630,
        alt: `${caseName} case brief | ${BRAND_NAME}`,
      }

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
      images: [socialImage],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${caseName} | ${BRAND_NAME}`,
      description: `Case brief for ${caseName}`,
      images: [socialImage.url],
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
