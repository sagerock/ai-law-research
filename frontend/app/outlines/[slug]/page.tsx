import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Header from '@/components/Header'
import { API_URL } from '@/lib/api'
import { BRAND_NAME, SITE_URL, SOCIAL_IMAGE, SOCIAL_IMAGE_PATH } from '@/lib/site'
import type { CanonicalOutline } from '@/types'
import CanonicalOutlineClient from './CanonicalOutlineClient'

interface PageProps {
  params: Promise<{ slug: string }>
}

async function getOutline(slug: string): Promise<CanonicalOutline | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/canonical-outlines/${slug}`, {
      next: { revalidate: 300 },
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const outline = await getOutline(slug)
  if (!outline) return { title: 'Outline Not Found' }

  const description = outline.description || `A free ${outline.subject} outline for law students.`
  const canonical = `${SITE_URL}/outlines/${outline.slug}`
  return {
    title: outline.title,
    description,
    alternates: { canonical },
    openGraph: {
      title: `${outline.title} | ${BRAND_NAME}`,
      description,
      type: 'article',
      url: canonical,
      images: [SOCIAL_IMAGE],
    },
    twitter: {
      card: 'summary_large_image',
      title: `${outline.title} | ${BRAND_NAME}`,
      description,
      images: [SOCIAL_IMAGE_PATH],
    },
  }
}

export default async function CanonicalOutlinePage({ params }: PageProps) {
  const { slug } = await params
  const outline = await getOutline(slug)
  if (!outline) notFound()

  return (
    <>
      <Header />
      <CanonicalOutlineClient initialOutline={outline} />
    </>
  )
}
