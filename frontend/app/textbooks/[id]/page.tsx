import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import TextbookDetailClient from './TextbookDetailClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface TextbookData {
  id: number
  title: string
  edition: string | null
  authors: string | null
  subject: string | null
  isbn: string | null
  year: number | null
  cases: Array<{
    id: string
    title: string
    reporter_cite: string | null
    decision_date: string | null
    court_name: string | null
    has_brief: boolean
    chapter: string | null
    sort_order: number | null
    case_name_in_book: string | null
  }>
  pending_count: number
}

interface PageProps {
  params: Promise<{ id: string }>
}

async function getTextbook(id: string): Promise<TextbookData | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/textbooks/${id}`, {
      next: { revalidate: 3600 }
    })
    if (!response.ok) return null
    return response.json()
  } catch (error) {
    console.error('Failed to fetch textbook:', error)
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  const data = await getTextbook(id)

  if (!data) {
    return { title: 'Textbook Not Found' }
  }

  const editionStr = data.edition ? `, ${data.edition} Ed.` : ''
  return {
    title: `${data.title}${editionStr}`,
    description: `Browse ${data.cases.length} case briefs from ${data.title}${editionStr}. Free case briefs for law students.`,
    openGraph: {
      title: `${data.title}${editionStr} | Law Study Group`,
      description: `${data.cases.length} case briefs from this casebook`,
      type: 'article',
    },
  }
}

export default async function TextbookDetailPage({ params }: PageProps) {
  const { id } = await params
  const data = await getTextbook(id)

  if (!data) {
    notFound()
  }

  return <TextbookDetailClient textbook={data} />
}
