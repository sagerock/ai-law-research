'use client'

import { useState, useEffect, useMemo } from 'react'
import { Scale, BookOpen, Search, Heart, Upload, MessageCircle, FileText } from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import { UserMenu } from '@/components/auth/UserMenu'

interface CasebookCase {
  id: string
  title: string
  reporter_cite: string
  decision_date: string | null
  court_name: string | null
  subject: string | null
}

export default function HomePage() {
  const [cases, setCases] = useState<CasebookCase[]>([])
  const [query, setQuery] = useState('')
  const [subjectFilter, setSubjectFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/casebook-cases`)
      .then(res => res.json())
      .then(data => {
        setCases(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    return cases.filter(c => {
      if (subjectFilter !== 'all' && c.subject !== subjectFilter) return false
      if (!q) return true
      return c.title.toLowerCase().includes(q)
        || (c.reporter_cite && c.reporter_cite.toLowerCase().includes(q))
    })
  }, [cases, query, subjectFilter])

  const subjects = useMemo(() => {
    const s = new Set(cases.map(c => c.subject).filter(Boolean))
    return Array.from(s).sort()
  }, [cases])

  const year = (d: string | null) => d ? d.slice(0, 4) : ''

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50 overflow-visible">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Sage's Law School Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
              </div>
            </div>
            <nav className="flex items-center space-x-4 sm:space-x-6">
              <Link
                href="/briefcheck"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <Upload className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Brief Check</span>
              </Link>
              <Link
                href="/transparency"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <Heart className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Transparency</span>
              </Link>
              <Link
                href="/library"
                className="text-neutral-600 hover:text-neutral-900 transition hidden sm:flex items-center"
              >
                <BookOpen className="h-5 w-5 mr-2" />
                My Library
              </Link>
              <Link
                href="/outlines"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <FileText className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Outlines</span>
              </Link>
              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <MessageCircle className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Discord</span>
              </a>
              <UserMenu />
            </nav>
          </div>
        </div>
      </header>

      {/* Search Section */}
      <section className="py-10 px-4">
        <div className="container mx-auto max-w-3xl text-center">
          <div className="flex items-center justify-center mb-3">
            <BookOpen className="h-7 w-7 text-purple-600 mr-3" />
            <h2 className="text-3xl font-bold text-neutral-900">Casebook Lookup</h2>
          </div>
          <p className="text-neutral-600 mb-8">
            Instant search across {cases.length || '...'} cases from your law school casebooks.
            Each case has a full AI brief ready to read.
          </p>

          {/* Search input */}
          <div className="relative max-w-xl mx-auto mb-4">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-neutral-400" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search cases by name or citation..."
              autoFocus
              className="w-full pl-12 pr-4 py-3.5 border-2 border-neutral-200 rounded-xl
                         text-lg focus:border-purple-500 focus:outline-none transition-colors
                         bg-white shadow-sm"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400
                           hover:text-neutral-600 text-sm font-medium"
              >
                Clear
              </button>
            )}
          </div>

          {/* Subject filter pills */}
          {subjects.length > 1 && (
            <div className="flex justify-center gap-2 mb-2">
              <button
                onClick={() => setSubjectFilter('all')}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  subjectFilter === 'all'
                    ? 'bg-neutral-900 text-white'
                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                }`}
              >
                All ({cases.length})
              </button>
              {subjects.map(s => {
                const count = cases.filter(c => c.subject === s).length
                return (
                  <button
                    key={s}
                    onClick={() => setSubjectFilter(s!)}
                    className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                      subjectFilter === s
                        ? 'bg-neutral-900 text-white'
                        : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                    }`}
                  >
                    {s} ({count})
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </section>

      {/* Results */}
      <section className="px-4 pb-16">
        <div className="container mx-auto max-w-3xl">
          {loading ? (
            <div className="text-center py-12 text-neutral-500">Loading cases...</div>
          ) : (
            <>
              <div className="text-sm text-neutral-500 mb-3">
                {filtered.length === cases.length
                  ? `${cases.length} cases`
                  : `${filtered.length} of ${cases.length} cases`}
              </div>

              {filtered.length === 0 && query ? (
                <div className="text-center py-12">
                  <p className="text-neutral-500 text-lg">No cases match &ldquo;{query}&rdquo;</p>
                  <p className="text-neutral-400 text-sm mt-2">Try a shorter search or different spelling</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {filtered.map(c => (
                    <Link
                      key={c.id}
                      href={`/case/${c.id}`}
                      className="flex items-baseline justify-between gap-4 px-4 py-3 rounded-lg
                                 hover:bg-purple-50 transition-colors group"
                    >
                      <div className="min-w-0">
                        <span className="font-medium text-neutral-900 group-hover:text-purple-700 transition-colors">
                          {c.title}
                        </span>
                        {c.court_name && (
                          <span className="text-neutral-400 text-sm ml-2 hidden sm:inline">
                            &mdash; {c.court_name}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 shrink-0 text-sm text-neutral-500">
                        <span className="hidden sm:inline">{c.reporter_cite}</span>
                        <span className="text-neutral-400">{year(c.decision_date)}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  )
}
