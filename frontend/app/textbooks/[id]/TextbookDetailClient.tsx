'use client'

import { useState } from 'react'
import { Search, ArrowLeft, Library, CheckCircle, Clock } from 'lucide-react'
import Link from 'next/link'
import Header from '@/components/Header'

interface CaseItem {
  id: string
  title: string
  reporter_cite: string | null
  decision_date: string | null
  court_name: string | null
  has_brief: boolean
  chapter: string | null
  sort_order: number | null
  case_name_in_book: string | null
}

interface TextbookData {
  id: number
  title: string
  edition: string | null
  authors: string | null
  subject: string | null
  isbn: string | null
  year: number | null
  cases: CaseItem[]
  pending_count: number
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

export default function TextbookDetailClient({ textbook }: { textbook: TextbookData }) {
  const [filter, setFilter] = useState('')

  const filtered = textbook.cases.filter(c => {
    if (!filter.trim()) return true
    const q = filter.toLowerCase()
    const name = (c.case_name_in_book || c.title || '').toLowerCase()
    const cite = (c.reporter_cite || '').toLowerCase()
    return name.includes(q) || cite.includes(q)
  })

  // Check if any case has a chapter
  const hasChapters = textbook.cases.some(c => c.chapter)

  // Group by chapter if chapters exist
  const grouped: Record<string, CaseItem[]> = {}
  if (hasChapters) {
    for (const c of filtered) {
      const key = c.chapter || 'Other'
      if (!grouped[key]) grouped[key] = []
      grouped[key].push(c)
    }
  }

  const briefCount = textbook.cases.filter(c => c.has_brief).length

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      <section className="py-8 px-4">
        <div className="container mx-auto max-w-3xl">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-1.5 text-sm text-stone-500 mb-4">
            <Link href="/" className="hover:text-stone-700">Home</Link>
            <span>/</span>
            <Link href="/textbooks" className="hover:text-stone-700">Textbooks</Link>
            <span>/</span>
            <span className="text-stone-700 truncate">{textbook.title}</span>
          </div>

          {/* Header */}
          <div className="mb-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-stone-900">
                  {textbook.title}
                </h1>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-stone-600">
                  {textbook.edition && <span>{textbook.edition} Edition</span>}
                  {textbook.authors && <span className="text-sm">{textbook.authors}</span>}
                </div>
              </div>
              {textbook.subject && (
                <span className="inline-block px-2.5 py-1 text-xs font-medium bg-sage-50 text-sage-700
                               rounded-full whitespace-nowrap flex-shrink-0 mt-1">
                  {subjectLabel(textbook.subject)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-3 text-sm text-stone-600">
              <span>{textbook.cases.length} cases</span>
              <span className="flex items-center gap-1">
                <CheckCircle className="h-3.5 w-3.5 text-sage-600" />
                {briefCount} briefs available
              </span>
            </div>
          </div>

          {/* Search filter */}
          {textbook.cases.length > 10 && (
            <div className="relative max-w-xl mb-6">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-stone-400" />
              <input
                type="text"
                value={filter}
                onChange={e => setFilter(e.target.value)}
                placeholder="Filter cases..."
                className="w-full pl-12 pr-4 py-3 border-2 border-stone-200 rounded-xl
                           text-lg focus:border-sage-500 focus:outline-none transition-colors
                           bg-white shadow-sm"
              />
              {filter && (
                <button
                  onClick={() => setFilter('')}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-stone-400
                             hover:text-stone-600 text-sm font-medium"
                >
                  Clear
                </button>
              )}
            </div>
          )}

          {/* Pending imports notice */}
          {textbook.pending_count > 0 && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 mb-6 text-sm text-amber-800">
              <Clock className="h-4 w-4 flex-shrink-0" />
              {textbook.pending_count} additional cases being imported
            </div>
          )}

          {/* Case list */}
          {hasChapters ? (
            <div className="space-y-8">
              {Object.entries(grouped).map(([chapter, cases]) => (
                <div key={chapter}>
                  <h3 className="text-lg font-semibold text-stone-900 mb-3">{chapter}</h3>
                  <CaseList cases={cases} />
                </div>
              ))}
            </div>
          ) : (
            <CaseList cases={filtered} numbered />
          )}

          {filter && filtered.length === 0 && (
            <p className="text-stone-500 text-center py-8">No cases match &ldquo;{filter}&rdquo;</p>
          )}
        </div>
      </section>
    </div>
  )
}

function CaseList({ cases, numbered = false }: { cases: CaseItem[], numbered?: boolean }) {
  return (
    <div className="space-y-1">
      {cases.map((c, i) => (
        <Link
          key={c.id}
          href={`/case/${c.id}`}
          className="flex items-center gap-3 py-2.5 px-3 rounded-lg
                     hover:bg-sage-50 transition-colors group"
        >
          {numbered && (
            <span className="text-sm text-stone-400 w-7 text-right flex-shrink-0">
              {(c.sort_order ?? i) + 1}.
            </span>
          )}
          <div className="min-w-0 flex-1">
            <span className="text-stone-800 group-hover:text-sage-700 transition-colors">
              {c.case_name_in_book || c.title}
            </span>
            {c.reporter_cite && (
              <span className="text-sm text-stone-500 ml-2">{c.reporter_cite}</span>
            )}
          </div>
          {c.has_brief && (
            <span className="flex items-center gap-1 text-xs text-sage-600 flex-shrink-0">
              <CheckCircle className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Brief</span>
            </span>
          )}
        </Link>
      ))}
    </div>
  )
}
