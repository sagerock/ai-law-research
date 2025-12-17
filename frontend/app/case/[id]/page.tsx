import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import CaseDetailClient, { CaseDetail } from './CaseDetailClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps {
  params: Promise<{ id: string }>
}

async function getCase(id: string): Promise<CaseDetail | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/${id}`, {
      next: { revalidate: 3600 } // Cache for 1 hour
    })
    if (!response.ok) return null
    return response.json()
  } catch (error) {
    console.error('Failed to fetch case:', error)
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  const caseData = await getCase(id)

  if (!caseData) {
    return {
      title: 'Case Not Found | Sage\'s Study Group',
    }
  }

  const caseName = caseData.title || caseData.case_name || 'Unknown Case'
  const court = caseData.court_name || caseData.court_id || ''
  const year = caseData.decision_date
    ? new Date(caseData.decision_date).getFullYear()
    : caseData.date_filed
      ? new Date(caseData.date_filed).getFullYear()
      : ''

  return {
    title: `${caseName} | Sage's Study Group`,
    description: `Read the full case brief for ${caseName}${court ? ` (${court}${year ? `, ${year}` : ''})` : ''}. Free AI-powered case summaries for law students.`,
    openGraph: {
      title: `${caseName} | Sage's Study Group`,
      description: `Case brief and AI summary for ${caseName}`,
      type: 'article',
    },
  }
}

export default async function CaseDetailPage({ params }: PageProps) {
  const { id } = await params
  const caseData = await getCase(id)

  if (!caseData) {
    notFound()
  }

  return <CaseDetailClient caseData={caseData} caseId={id} />
}
