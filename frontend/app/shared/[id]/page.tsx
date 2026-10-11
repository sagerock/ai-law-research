import { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { User, FolderOpen } from 'lucide-react'
import Header from '@/components/Header'
import SharedCollectionItems, { type SharedCase, type SharedLegalText } from '@/components/SharedCollectionItems'
import { BRAND_NAME, SITE_TAGLINE, SITE_URL, SOCIAL_IMAGE } from '@/lib/site'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
      title: `${collection.name} | ${BRAND_NAME}`,
      description,
      type: 'article',
      url: `${SITE_URL}/shared/${id}`,
      images: [SOCIAL_IMAGE],
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

          <SharedCollectionItems
            collectionId={id}
            cases={collection.cases}
            legalTexts={collection.legal_texts || []}
          />

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
          <p>{BRAND_NAME} - {SITE_TAGLINE}</p>
        </div>
      </footer>
    </div>
  )
}
