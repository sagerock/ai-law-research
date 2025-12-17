import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { Scale, Calendar, User, FolderOpen, ExternalLink } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://ai-law-research-production.up.railway.app'

interface SharedCollection {
  id: string
  name: string
  description: string | null
  subject: string | null
  owner_name: string
  created_at: string | null
  cases: SharedCase[]
  case_count: number
}

interface SharedCase {
  id: string
  title: string
  decision_date: string | null
  reporter_cite: string | null
  court_name: string | null
  notes: string | null
}

interface PageProps {
  params: Promise<{ id: string }>
}

async function getSharedCollection(id: string): Promise<SharedCollection | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/shared/${id}`, {
      next: { revalidate: 60 } // Cache for 1 minute
    })
    if (!response.ok) return null
    return response.json()
  } catch (error) {
    console.error('Failed to fetch shared collection:', error)
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  const collection = await getSharedCollection(id)

  if (!collection) {
    return {
      title: 'Collection Not Found | Sage\'s Study Group',
    }
  }

  const description = collection.description
    || `A collection of ${collection.case_count} cases${collection.subject ? ` about ${collection.subject}` : ''} by ${collection.owner_name}`

  return {
    title: `${collection.name} | Sage's Study Group`,
    description,
    openGraph: {
      title: `${collection.name} | Sage's Study Group`,
      description,
      type: 'article',
      url: `${SITE_URL}/shared/${id}`,
    },
  }
}

export default async function SharedCollectionPage({ params }: PageProps) {
  const { id } = await params
  const collection = await getSharedCollection(id)

  if (!collection) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Sage's Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
              </div>
            </Link>
            <nav className="flex items-center gap-4">
              <Link href="/" className="text-neutral-600 hover:text-neutral-900 transition">
                Search Cases
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Collection Header */}
          <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-8 mb-8">
            <div className="flex items-start gap-4 mb-6">
              <div className="p-3 bg-blue-100 rounded-lg">
                <FolderOpen className="h-8 w-8 text-blue-600" />
              </div>
              <div className="flex-1">
                <h1 className="text-3xl font-bold text-neutral-900 mb-2">
                  {collection.name}
                </h1>
                {collection.description && (
                  <p className="text-neutral-600 text-lg mb-4">
                    {collection.description}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-500">
                  <span className="flex items-center gap-1">
                    <User className="h-4 w-4" />
                    Shared by {collection.owner_name}
                  </span>
                  {collection.subject && (
                    <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                      {collection.subject}
                    </span>
                  )}
                  <span>
                    {collection.case_count} {collection.case_count === 1 ? 'case' : 'cases'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Cases List */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-neutral-900 mb-4">
              Cases in this Collection
            </h2>

            {collection.cases.length === 0 ? (
              <div className="text-center py-12 text-neutral-500">
                <p>This collection is empty</p>
              </div>
            ) : (
              collection.cases.map(caseItem => (
                <Link
                  key={caseItem.id}
                  href={`/case/${caseItem.id}`}
                  className="block bg-white rounded-lg border border-neutral-200 p-5 hover:border-blue-300 hover:shadow-md transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-neutral-900 text-lg hover:text-blue-600 transition">
                        {caseItem.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-neutral-500">
                        {caseItem.court_name && (
                          <span>{caseItem.court_name}</span>
                        )}
                        {caseItem.decision_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {new Date(caseItem.decision_date).getFullYear()}
                          </span>
                        )}
                        {caseItem.reporter_cite && (
                          <span className="text-neutral-400">{caseItem.reporter_cite}</span>
                        )}
                      </div>
                      {caseItem.notes && (
                        <p className="mt-3 text-sm text-neutral-600 italic border-l-2 border-blue-200 pl-3">
                          {caseItem.notes}
                        </p>
                      )}
                    </div>
                    <ExternalLink className="h-5 w-5 text-neutral-400 flex-shrink-0 ml-4" />
                  </div>
                </Link>
              ))
            )}
          </div>

          {/* Footer CTA */}
          <div className="mt-12 text-center">
            <p className="text-neutral-600 mb-4">
              Want to create your own case collections?
            </p>
            <Link
              href="/login"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
            >
              Sign up for free
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-white mt-16">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-neutral-500">
          <p>Sage's Study Group - Free AI Case Briefs for Law Students</p>
        </div>
      </footer>
    </div>
  )
}
