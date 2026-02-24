import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import StatuteDetailClient from './StatuteDetailClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps {
  params: Promise<{ slug: string }>
}

async function getStatute(slug: string) {
  try {
    const response = await fetch(`${API_URL}/api/v1/legal-texts/federal_statutes/${slug}`, {
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
  const data = await getStatute(slug)

  if (!data) {
    return { title: 'Statute Not Found' }
  }

  const title = data.citation
    ? `${data.citation} - ${data.title}`
    : data.title

  return {
    title,
    description: `Full text of ${title}. Federal statute reference for law students.`,
    openGraph: {
      title: `${title} | Federal Statutes`,
      description: `Read the full text of ${title}`,
      type: 'article',
    },
  }
}

export default async function StatuteDetailPage({ params }: PageProps) {
  const { slug } = await params
  const data = await getStatute(slug)

  if (!data) {
    notFound()
  }

  return <StatuteDetailClient data={data} />
}
