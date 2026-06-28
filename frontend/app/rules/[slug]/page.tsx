import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import RuleDetailClient from './RuleDetailClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps {
  params: Promise<{ slug: string }>
}

// FRCP is numbered 1–86; FRE is 101–1103 — no overlap, so the rule number
// alone tells us which document a "rule-N" slug belongs to.
function docForSlug(slug: string): 'fre' | 'frcp' {
  const m = slug.match(/rule-(\d+)/)
  const n = m ? parseInt(m[1], 10) : 0
  return n >= 101 ? 'fre' : 'frcp'
}

async function getRule(slug: string) {
  const doc = docForSlug(slug)
  try {
    const response = await fetch(`${API_URL}/api/v1/legal-texts/${doc}/${slug}`, {
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
  const corpus = docForSlug(slug) === 'fre'
    ? 'Federal Rules of Evidence'
    : 'Federal Rules of Civil Procedure'
  const abbr = docForSlug(slug) === 'fre' ? 'FRE' : 'FRCP'

  return {
    title,
    description: `${corpus} ${title}. Full text with subsections.`,
    openGraph: {
      title: `${title} | ${abbr}`,
      description: `Read the full text of ${abbr} ${title}`,
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
