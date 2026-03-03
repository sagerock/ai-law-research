import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { Calendar, User, FolderOpen, ExternalLink } from 'lucide-react'
import Header from '@/components/Header'

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
  legal_texts: SharedLegalText[]
  case_count: number
  legal_text_count: number
  item_count: number
}

interface SharedCase {
  id: string
  title: string
  decision_date: string | null
  reporter_cite: string | null
  court_name: string | null
  notes: string | null
  position: number
}

interface SharedLegalText {
  item_id: number
  document_id: string
  slug: string
  title: string
  citation: string | null
  number: string | null
  notes: string | null
  position: number
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
      title: 'Collection Not Found',
    }
  }

  const totalItems = (collection.item_count ?? collection.case_count) || 0
  const description = collection.description
    || `A collection of ${totalItems} items${collection.subject ? ` about ${collection.subject}` : ''} by ${collection.owner_name}`

  return {
    title: collection.name,
    description,
    openGraph: {
      title: `${collection.name} | Law Study Group`,
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
    <div className="min-h-screen bg-cream">
      <Header />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Collection Header */}
          <div className="bg-white rounded-xl shadow-sm border border-stone-200 p-8 mb-8">
            <div className="flex items-start gap-4 mb-6">
              <div className="p-3 bg-sage-50 rounded-lg">
                <FolderOpen className="h-8 w-8 text-sage-600" />
              </div>
              <div className="flex-1">
                <h1 className="text-3xl font-bold text-stone-900 mb-2">
                  {collection.name}
                </h1>
                {collection.description && (
                  <p className="text-stone-600 text-lg mb-4">
                    {collection.description}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-4 text-sm text-stone-500">
                  <span className="flex items-center gap-1">
                    <User className="h-4 w-4" />
                    Shared by {collection.owner_name}
                  </span>
                  {collection.subject && (
                    <span className="bg-sage-50 text-sage-700 px-2 py-0.5 rounded">
                      {collection.subject}
                    </span>
                  )}
                  <span>
                    {(collection.item_count ?? collection.case_count)} {(collection.item_count ?? collection.case_count) === 1 ? 'item' : 'items'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* All Items — unified list */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-stone-900 mb-4">
              Items in this Collection
            </h2>

            {collection.cases.length === 0 && (!collection.legal_texts || collection.legal_texts.length === 0) ? (
              <div className="text-center py-12 text-stone-500">
                <p>This collection is empty</p>
              </div>
            ) : (
              [...collection.cases.map(c => ({
                type: 'case' as const,
                key: `case-${c.id}`,
                position: c.position ?? 0,
                data: c
              })),
              ...(collection.legal_texts || []).map(lt => ({
                type: 'legal_text' as const,
                key: `lt-${lt.item_id}`,
                position: lt.position ?? 0,
                data: lt
              }))]
              .sort((a, b) => a.position - b.position)
              .map(item => {
                if (item.type === 'case') {
                  const caseItem = item.data as SharedCase
                  return (
                    <Link
                      key={item.key}
                      href={`/case/${caseItem.id}?shared_collection=${id}`}
                      className="block bg-white rounded-lg border border-stone-200 p-5 hover:border-sage-200 hover:shadow-md transition"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs bg-sage-50 text-sage-700 px-2 py-0.5 rounded font-medium">
                              Case
                            </span>
                          </div>
                          <h3 className="font-semibold text-stone-900 text-lg hover:text-sage-600 transition">
                            {caseItem.title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-stone-500">
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
                              <span className="text-stone-400">{caseItem.reporter_cite}</span>
                            )}
                          </div>
                          {caseItem.notes && (
                            <p className="mt-3 text-sm text-stone-600 italic border-l-2 border-sage-200 pl-3">
                              {caseItem.notes}
                            </p>
                          )}
                        </div>
                        <ExternalLink className="h-5 w-5 text-stone-400 flex-shrink-0 ml-4" />
                      </div>
                    </Link>
                  )
                } else {
                  const lt = item.data as SharedLegalText
                  const route = lt.document_id === 'frcp' ? '/rules'
                    : lt.document_id === 'constitution' ? '/constitution'
                    : '/statutes'
                  const typeLabel = lt.document_id === 'frcp' ? 'FRCP'
                    : lt.document_id === 'constitution' ? 'Constitution'
                    : 'Statute'
                  return (
                    <Link
                      key={item.key}
                      href={`${route}/${lt.slug}`}
                      className="block bg-white rounded-lg border border-stone-200 p-5 hover:border-sage-300 hover:shadow-md transition"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs bg-sage-50 text-sage-700 px-2 py-0.5 rounded font-medium">
                              {typeLabel}
                            </span>
                          </div>
                          <h3 className="font-semibold text-stone-900 text-lg hover:text-sage-600 transition">
                            {lt.number ? `${typeLabel} ${lt.number}` : lt.title}
                            {lt.number && lt.title ? ` \u2014 ${lt.title}` : ''}
                          </h3>
                          {lt.citation && (
                            <p className="text-sm text-stone-400 mt-1">{lt.citation}</p>
                          )}
                          {lt.notes && (
                            <p className="mt-3 text-sm text-stone-600 italic border-l-2 border-sage-200 pl-3">
                              {lt.notes}
                            </p>
                          )}
                        </div>
                        <ExternalLink className="h-5 w-5 text-stone-400 flex-shrink-0 ml-4" />
                      </div>
                    </Link>
                  )
                }
              })
            )}
          </div>

          {/* Footer CTA */}
          <div className="mt-12 text-center">
            <p className="text-stone-600 mb-4">
              Want to create your own case collections?
            </p>
            <Link
              href="/login"
              className="inline-flex items-center px-6 py-3 bg-sage-700 text-white rounded-lg font-medium hover:bg-sage-600 transition"
            >
              Sign up for free
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-white mt-16">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-stone-500">
          <p>Law Study Group - Free Case Briefs for Law Students</p>
        </div>
      </footer>
    </div>
  )
}
