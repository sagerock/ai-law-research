import { permanentRedirect } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps {
  params: Promise<{ id: string }>
}

async function resolveSlug(slug: string): Promise<{ case_id: string; canonical_slug: string } | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/resolve/${slug}`, {
      next: { revalidate: 86400 }
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export default async function CaseRedirectPage({ params }: PageProps) {
  const { id } = await params

  const resolved = await resolveSlug(id)
  if (!resolved) {
    // Fallback: try the old route directly in case resolve fails
    permanentRedirect(`/cases/${id}`)
  }

  permanentRedirect(`/cases/${resolved.canonical_slug}`)
}
