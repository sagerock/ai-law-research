'use client'

import { useState, useEffect } from 'react'
import { Library, ArrowLeft, BookOpen, CheckCircle } from 'lucide-react'
import Link from 'next/link'
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

export default function TextbooksPage() {
  const [textbooks, setTextbooks] = useState<Textbook[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/textbooks`)
      .then(res => res.json())
      .then(data => {
        setTextbooks(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  // Group by subject
  const grouped: Record<string, Textbook[]> = {}
  for (const tb of textbooks) {
    const key = subjectLabel(tb.subject)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(tb)
  }

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
            Browse case briefs organized by your law school casebook.
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
            <div className="space-y-8">
              {Object.entries(grouped).map(([subject, books]) => (
                <div key={subject}>
                  <h3 className="text-lg font-semibold text-stone-900 mb-3">{subject}</h3>
                  <div className="space-y-3">
                    {books.map(tb => (
                      <Link
                        key={tb.id}
                        href={`/textbooks/${tb.id}`}
                        className="block bg-white border border-stone-200 rounded-xl p-5
                                   hover:border-sage-300 hover:shadow-sm transition-all group"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            <h4 className="font-semibold text-stone-900 group-hover:text-sage-700 transition-colors">
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
                            </div>
                          </div>
                          <span className="inline-block px-2.5 py-1 text-xs font-medium bg-sage-50 text-sage-700
                                         rounded-full whitespace-nowrap flex-shrink-0">
                            {subjectLabel(tb.subject)}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
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
