'use client'

import { useState, useEffect } from 'react'
import { Library, ArrowLeft, BookOpen, CheckCircle, ChevronDown, Star } from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import Header from '@/components/Header'

interface Textbook {
  id: number
  title: string
  edition: string | null
  authors: string | null
  subject: string | null
  isbn: string | null
  year: number | null
  case_count: number
  brief_count: number
}

const SUBJECT_LABELS: Record<string, string> = {
  criminal_law: 'Criminal Law',
  torts: 'Torts',
  contracts: 'Contracts',
  con_law: 'Constitutional Law',
  civ_pro: 'Civil Procedure',
  property: 'Property',
  crim_pro: 'Criminal Procedure',
  evidence: 'Evidence',
}

function subjectLabel(subject: string | null): string {
  if (!subject) return 'General'
  return SUBJECT_LABELS[subject] || subject.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function TextbookCard({ tb, bookmarked, onToggleBookmark, showSubject }: {
  tb: Textbook
  bookmarked: boolean
  onToggleBookmark: (id: number) => void
  showSubject?: boolean
}) {
  return (
    <div className="flex items-start gap-3 bg-stone-50 border border-stone-200 rounded-lg p-4
                    hover:border-sage-300 hover:bg-white hover:shadow-sm transition-all group/card">
      <Link
        href={`/textbooks/${tb.id}`}
        className="flex-1 min-w-0"
      >
        <h4 className="font-semibold text-stone-900 group-hover/card:text-sage-700 transition-colors">
          {tb.title}
          {tb.edition && <span className="text-stone-500 font-normal">, {tb.edition} Ed.</span>}
        </h4>
        {tb.authors && (
          <p className="text-sm text-stone-500 mt-0.5">{tb.authors}</p>
        )}
        <div className="flex items-center gap-4 mt-2 text-sm text-stone-600">
          <span className="flex items-center gap-1">
            <BookOpen className="h-3.5 w-3.5" />
            {tb.case_count} cases
          </span>
          <span className="flex items-center gap-1">
            <CheckCircle className="h-3.5 w-3.5 text-sage-600" />
            {tb.brief_count} briefs available
          </span>
          {showSubject && (
            <span className="inline-block px-2 py-0.5 text-xs font-medium bg-sage-50 text-sage-700 rounded-full">
              {subjectLabel(tb.subject)}
            </span>
          )}
        </div>
      </Link>
      <button
        onClick={(e) => { e.preventDefault(); onToggleBookmark(tb.id) }}
        className={`p-1.5 rounded-lg transition-colors shrink-0 ${
          bookmarked
            ? 'text-amber-500 hover:text-amber-600'
            : 'text-stone-300 hover:text-amber-400'
        }`}
        title={bookmarked ? 'Remove from My Textbooks' : 'Save to My Textbooks'}
      >
        <Star className={`h-5 w-5 ${bookmarked ? 'fill-current' : ''}`} />
      </button>
    </div>
  )
}

function SubjectGroup({ subject, books, bookmarkedIds, onToggleBookmark }: {
  subject: string
  books: Textbook[]
  bookmarkedIds: Set<number>
  onToggleBookmark: (id: number) => void
}) {
  const [open, setOpen] = useState(false)
  const totalCases = books.reduce((sum, b) => sum + b.case_count, 0)

  return (
    <div className="border border-stone-200 rounded-xl bg-white overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-5 py-4 flex items-center justify-between gap-3 hover:bg-stone-50 transition-colors group"
      >
        <div className="flex items-center gap-3 min-w-0">
          <h3 className="text-lg font-semibold text-stone-900 group-hover:text-sage-700 transition-colors">{subject}</h3>
          <span className="text-xs text-stone-400 font-medium">
            {books.length} book{books.length !== 1 ? 's' : ''} · {totalCases} cases
          </span>
        </div>
        <ChevronDown className={`h-5 w-5 text-stone-400 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      <div
        className="grid transition-[grid-template-rows] duration-200 ease-out"
        style={{ gridTemplateRows: open ? '1fr' : '0fr' }}
      >
        <div className="overflow-hidden">
          <div className="px-5 pb-4 space-y-3 border-t border-stone-100 pt-3">
            {books.map(tb => (
              <TextbookCard
                key={tb.id}
                tb={tb}
                bookmarked={bookmarkedIds.has(tb.id)}
                onToggleBookmark={onToggleBookmark}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function TextbooksPage() {
  const { session } = useAuth()
  const [textbooks, setTextbooks] = useState<Textbook[]>([])
  const [loading, setLoading] = useState(true)
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    fetch(`${API_URL}/api/v1/textbooks`)
      .then(res => res.json())
      .then(data => {
        setTextbooks(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  // Fetch bookmarked textbook IDs if logged in
  useEffect(() => {
    if (!session?.access_token) return
    fetch(`${API_URL}/api/v1/library/textbook-bookmarks/check`, {
      headers: { 'Authorization': `Bearer ${session.access_token}` }
    })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.bookmarked_ids) {
          setBookmarkedIds(new Set(data.bookmarked_ids))
        }
      })
      .catch(() => {})
  }, [session?.access_token])

  function toggleBookmark(textbookId: number) {
    if (!session?.access_token) return
    const isBookmarked = bookmarkedIds.has(textbookId)

    // Optimistic update
    setBookmarkedIds(prev => {
      const next = new Set(prev)
      if (isBookmarked) next.delete(textbookId)
      else next.add(textbookId)
      return next
    })

    if (isBookmarked) {
      fetch(`${API_URL}/api/v1/library/textbook-bookmarks/${textbookId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      }).catch(() => {
        // Revert on error
        setBookmarkedIds(prev => { const next = new Set(prev); next.add(textbookId); return next })
      })
    } else {
      fetch(`${API_URL}/api/v1/library/textbook-bookmarks`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ textbook_id: textbookId })
      }).catch(() => {
        // Revert on error
        setBookmarkedIds(prev => { const next = new Set(prev); next.delete(textbookId); return next })
      })
    }
  }

  // Group by subject
  const grouped: Record<string, Textbook[]> = {}
  for (const tb of textbooks) {
    const key = subjectLabel(tb.subject)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(tb)
  }

  // Bookmarked textbooks for "My Textbooks" section
  const myTextbooks = textbooks.filter(tb => bookmarkedIds.has(tb.id))

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      <section className="py-8 px-4">
        <div className="container mx-auto max-w-3xl">
          <Link href="/" className="inline-flex items-center text-sm text-stone-500 hover:text-stone-700 mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> Home
          </Link>

          <div className="flex items-center gap-3 mb-2">
            <Library className="h-7 w-7 text-sage-600" />
            <h2 className="text-3xl font-bold text-stone-900">Textbooks</h2>
          </div>
          <p className="text-stone-600 mb-8">
            Browse case briefs organized by your law school casebook.{' '}
            {session ? 'Star a textbook to save it for quick access.' : ''}
          </p>

          {loading ? (
            <p className="text-stone-500">Loading textbooks...</p>
          ) : textbooks.length === 0 ? (
            <div className="bg-white border border-stone-200 rounded-xl p-8 text-center">
              <Library className="h-10 w-10 text-stone-300 mx-auto mb-3" />
              <p className="text-stone-600 mb-2">No textbooks available yet.</p>
              <p className="text-sm text-stone-500">
                More textbooks coming soon &mdash;{' '}
                <a href="https://discord.gg/AcGcKMmMZX" target="_blank" rel="noopener noreferrer"
                   className="text-sage-600 hover:text-sage-700 underline">
                  request yours on Discord
                </a>
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* My Textbooks — pinned at top */}
              {myTextbooks.length > 0 && (
                <div className="border border-amber-200 rounded-xl bg-amber-50/50 overflow-hidden mb-5">
                  <div className="px-5 py-3 flex items-center gap-2 border-b border-amber-200/60">
                    <Star className="h-4 w-4 text-amber-500 fill-current" />
                    <h3 className="text-sm font-semibold text-amber-800">My Textbooks</h3>
                  </div>
                  <div className="px-5 py-3 space-y-3">
                    {myTextbooks.map(tb => (
                      <TextbookCard
                        key={tb.id}
                        tb={tb}
                        bookmarked={true}
                        onToggleBookmark={toggleBookmark}
                        showSubject
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* All textbooks by subject */}
              {Object.entries(grouped).map(([subject, books]) => (
                <SubjectGroup
                  key={subject}
                  subject={subject}
                  books={books}
                  bookmarkedIds={bookmarkedIds}
                  onToggleBookmark={toggleBookmark}
                />
              ))}

              <div className="bg-stone-50 border border-stone-200 rounded-xl p-6 text-center mt-8">
                <p className="text-stone-600 text-sm">
                  More textbooks coming soon &mdash;{' '}
                  <a href="https://discord.gg/AcGcKMmMZX" target="_blank" rel="noopener noreferrer"
                     className="text-sage-600 hover:text-sage-700 underline">
                    request yours on Discord
                  </a>
                </p>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
