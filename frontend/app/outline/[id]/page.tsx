import OutlineDetail from './OutlineDetail'
import { BRAND_NAME } from '@/lib/site'

export const dynamic = 'force-dynamic'

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  try {
    const res = await fetch(`${API_URL}/api/v1/outlines/${id}`, { next: { revalidate: 60 } })
    if (!res.ok) return { title: `Outline | ${BRAND_NAME}` }
    const outline = await res.json()
    const parts = [outline.title]
    if (outline.subject) parts.push(outline.subject)
    return {
      title: `${parts.join(' — ')} | ${BRAND_NAME}`,
      description: outline.description || `${outline.subject} outline${outline.law_school ? ` from ${outline.law_school}` : ''}`,
    }
  } catch {
    return { title: `Outline | ${BRAND_NAME}` }
  }
}

export default async function OutlinePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <OutlineDetail outlineId={id} />
}
