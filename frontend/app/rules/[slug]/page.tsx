import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import RuleDetailClient from './RuleDetailClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps {
  params: Promise<{ slug: string }>
}

async function getRule(slug: string) {
  try {
    const response = await fetch(`${API_URL}/api/v1/legal-texts/frcp/${slug}`, {
      next: { revalidate: 86400 }
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const data = await getRule(slug)

  if (!data) {
    return { title: 'Rule Not Found' }
  }

  const title = data.number
    ? `Rule ${data.number} - ${data.title}`
    : data.title

  return {
    title,
    description: `Federal Rules of Civil Procedure ${title}. Full text with subsections.`,
    openGraph: {
      title: `${title} | FRCP`,
      description: `Read the full text of FRCP ${title}`,
      type: 'article',
    },
  }
}

export default async function RuleDetailPage({ params }: PageProps) {
  const { slug } = await params
  const data = await getRule(slug)

  if (!data) {
    notFound()
  }

  return <RuleDetailClient data={data} />
}
