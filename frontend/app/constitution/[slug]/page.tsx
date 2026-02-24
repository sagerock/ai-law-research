import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import ConstitutionDetailClient from './ConstitutionDetailClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps {
  params: Promise<{ slug: string }>
}

async function getItem(slug: string) {
  try {
    const response = await fetch(`${API_URL}/api/v1/legal-texts/constitution/${slug}`, {
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
  const data = await getItem(slug)

  if (!data) {
    return { title: 'Not Found' }
  }

  return {
    title: `${data.title} - U.S. Constitution`,
    description: `Full text of ${data.title} of the United States Constitution.`,
    openGraph: {
      title: `${data.title} | U.S. Constitution`,
      description: `Read the full text of ${data.title}`,
      type: 'article',
    },
  }
}

export default async function ConstitutionDetailPage({ params }: PageProps) {
  const { slug } = await params
  const data = await getItem(slug)

  if (!data) {
    notFound()
  }

  return <ConstitutionDetailClient data={data} />
}
