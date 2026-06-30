import { redirect, notFound } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps { params: Promise<{ id: string }> }

export default async function ReaderIndex({ params }: PageProps) {
  const { id } = await params
  let firstSlug: string | null = null
  try {
    const r = await fetch(`${API_URL}/api/v1/textbooks/${id}/contents`, { next: { revalidate: 3600 } })
    if (r.ok) {
      const toc = await r.json()
      firstSlug = toc?.chapters?.[0]?.slug ?? null
    }
  } catch { /* fall through */ }

  if (!firstSlug) notFound()
  redirect(`/textbooks/${id}/read/${firstSlug}`)
}
