'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { Scale, BookOpen, Search, MessageCircle, GraduationCap, ChevronDown, TrendingUp, ThumbsUp } from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import { UserMenu } from '@/components/auth/UserMenu'

interface CasebookCase {
  id: string
  title: string
  reporter_cite: string
  decision_date: string | null
  court_name: string | null
  has_brief: boolean
  subjects: string[]
  citation_count: number
}

interface TrendingCase {
  id: string
  title: string
  reporter_cite: string
  decision_date: string | null
  court_name: string | null
  has_brief: boolean
  thumbs_up: number
  thumbs_down: number
  comment_count: number
  engagement_score: number
}

type SortOption = 'most-cited' | 'newest' | 'oldest' | 'a-z'

interface SubjectCount {
  subject: string
  count: number
}

const PAGE_SIZE = 50

const TOP_SUBJECTS = [
  'torts', 'contracts', 'criminal-law', 'property',
  'employment-law', 'business-associations', 'remedies',
]

function formatSubject(slug: string): string {
  return slug
    .split('-')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export default function HomePage() {
  const [cases, setCases] = useState<CasebookCase[]>([])
  const [subjectCounts, setSubjectCounts] = useState<SubjectCount[]>([])
  const [query, setQuery] = useState('')
  const [subjectFilter, setSubjectFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)
  const [sortBy, setSortBy] = useState<SortOption>('most-cited')
  const [moreOpen, setMoreOpen] = useState(false)
  const [trendingCases, setTrendingCases] = useState<TrendingCase[]>([])
  const moreRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/casebook-cases`)
      .then(res => res.json())
      .then(data => {
        setCases(data.cases || [])
        setSubjectCounts(data.subject_counts || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))

    fetch(`${API_URL}/api/v1/trending-cases`)
      .then(res => res.json())
      .then(data => setTrendingCases(data.cases || []))
      .catch(() => {})
  }, [])

  // Close "More" dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false)
      }
    }
    if (moreOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [moreOpen])

  // Reset visible count when filters or sort change
  useEffect(() => {
    setVisibleCount(PAGE_SIZE)
  }, [query, subjectFilter, sortBy])

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim()
    const result = cases.filter(c => {
      if (subjectFilter !== 'all' && !c.subjects.includes(subjectFilter)) return false
      if (!q) return true
      return c.title.toLowerCase().includes(q)
        || (c.reporter_cite && c.reporter_cite.toLowerCase().includes(q))
    })
    if (sortBy === 'most-cited') {
      result.sort((a, b) => b.citation_count - a.citation_count || a.title.localeCompare(b.title))
    } else if (sortBy === 'newest') {
      result.sort((a, b) => (b.decision_date || '').localeCompare(a.decision_date || ''))
    } else if (sortBy === 'oldest') {
      result.sort((a, b) => (a.decision_date || '').localeCompare(b.decision_date || ''))
    } else {
      result.sort((a, b) => a.title.localeCompare(b.title))
    }
    return result
  }, [cases, query, subjectFilter, sortBy])

  const briefCount = useMemo(() => cases.filter(c => c.has_brief).length, [cases])

  // Split subjects into top pills and overflow
  const topPills = subjectCounts.filter(sc => TOP_SUBJECTS.includes(sc.subject))
    .sort((a, b) => TOP_SUBJECTS.indexOf(a.subject) - TOP_SUBJECTS.indexOf(b.subject))
  const overflowSubjects = subjectCounts.filter(sc => !TOP_SUBJECTS.includes(sc.subject))

  const year = (d: string | null) => d ? d.slice(0, 4) : ''

  const visible = filtered.slice(0, visibleCount)
  const hasMore = visibleCount < filtered.length

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50 overflow-visible">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Law Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free Case Briefs for Law Students</p>
              </div>
            </div>
            <nav className="flex items-center space-x-4 sm:space-x-6">
              <Link
                href="/study"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <GraduationCap className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Study</span>
              </Link>
              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
                title="Discord"
              >
                <MessageCircle className="h-5 w-5" />
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
            Search {cases.length ? cases.length.toLocaleString() : '...'} cases from law school casebooks.
            {briefCount > 0 && (
              <span className="text-purple-600 font-medium"> {briefCount.toLocaleString()} have AI briefs ready.</span>
            )}
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
          {subjectCounts.length > 1 && (
            <div className="flex flex-wrap justify-center gap-2 mb-2">
              <button
                onClick={() => setSubjectFilter('all')}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  subjectFilter === 'all'
                    ? 'bg-neutral-900 text-white'
                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                }`}
              >
                All ({cases.length.toLocaleString()})
              </button>
              {topPills.map(sc => (
                <button
                  key={sc.subject}
                  onClick={() => setSubjectFilter(sc.subject)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    subjectFilter === sc.subject
                      ? 'bg-neutral-900 text-white'
                      : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                  }`}
                >
                  {formatSubject(sc.subject)} ({sc.count.toLocaleString()})
                </button>
              ))}
              {overflowSubjects.length > 0 && (
                <div className="relative" ref={moreRef}>
                  <button
                    onClick={() => setMoreOpen(!moreOpen)}
                    className={`px-3 py-1 rounded-full text-sm font-medium transition-colors flex items-center gap-1 ${
                      moreOpen || (subjectFilter !== 'all' && !TOP_SUBJECTS.includes(subjectFilter))
                        ? 'bg-neutral-900 text-white'
                        : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                    }`}
                  >
                    More
                    <ChevronDown className={`h-3.5 w-3.5 transition-transform ${moreOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {moreOpen && (
                    <div className="absolute top-full mt-1 right-0 bg-white border border-neutral-200 rounded-lg
                                    shadow-lg max-h-64 overflow-y-auto w-56 z-50">
                      {overflowSubjects.map(sc => (
                        <button
                          key={sc.subject}
                          onClick={() => {
                            setSubjectFilter(sc.subject)
                            setMoreOpen(false)
                          }}
                          className={`w-full text-left px-3 py-2 text-sm hover:bg-purple-50 transition-colors flex justify-between ${
                            subjectFilter === sc.subject ? 'bg-purple-50 text-purple-700 font-medium' : 'text-neutral-700'
                          }`}
                        >
                          <span>{formatSubject(sc.subject)}</span>
                          <span className="text-neutral-400">{sc.count.toLocaleString()}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Trending Cases */}
      {trendingCases.length > 0 && (
        <section className="px-4 pb-6">
          <div className="container mx-auto max-w-3xl">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-5 w-5 text-purple-600" />
              <h3 className="text-lg font-semibold text-neutral-900">Trending Cases</h3>
              <span className="text-sm text-neutral-400 ml-1">Based on community activity</span>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-hide"
                 style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
              {trendingCases.map(tc => (
                <Link
                  key={tc.id}
                  href={`/case/${tc.id}`}
                  className="flex-shrink-0 w-64 bg-white border border-neutral-200 rounded-lg p-4
                             hover:border-purple-400 transition-colors group"
                >
                  <div className="mb-2">
                    <p className="font-medium text-neutral-900 group-hover:text-purple-700 transition-colors
                                  line-clamp-2 text-sm leading-snug">
                      {tc.title}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    {tc.has_brief && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px]
                                       font-semibold bg-purple-100 text-purple-700">
                        Brief
                      </span>
                    )}
                    {tc.court_name && (
                      <span className="text-xs text-neutral-400 truncate">{tc.court_name}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs text-neutral-500">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <ThumbsUp className="h-3 w-3" /> {tc.thumbs_up}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageCircle className="h-3 w-3" /> {tc.comment_count}
                      </span>
                    </div>
                    <span className="text-neutral-400">{tc.reporter_cite}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Results */}
      <section className="px-4 pb-16">
        <div className="container mx-auto max-w-3xl">
          {loading ? (
            <div className="text-center py-12 text-neutral-500">Loading cases...</div>
          ) : (
            <>
              <div className="text-sm text-neutral-500 mb-3 flex items-center justify-between">
                <span>
                  {filtered.length === cases.length
                    ? `${cases.length.toLocaleString()} cases`
                    : `${filtered.length.toLocaleString()} of ${cases.length.toLocaleString()} cases`}
                </span>
                <select
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value as SortOption)}
                  className="text-sm border border-neutral-200 rounded-md px-2 py-1 bg-white
                             text-neutral-600 focus:outline-none focus:border-purple-400 cursor-pointer"
                >
                  <option value="most-cited">Most Cited</option>
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="a-z">A–Z</option>
                </select>
              </div>

              {filtered.length === 0 && query ? (
                <div className="text-center py-12">
                  <p className="text-neutral-500 text-lg">No cases match &ldquo;{query}&rdquo;</p>
                  <p className="text-neutral-400 text-sm mt-2">Try a shorter search or different spelling</p>
                </div>
              ) : (
                <>
                  <div className="space-y-1">
                    {visible.map(c => (
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
                          {c.has_brief && (
                            <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px]
                                             font-semibold bg-purple-100 text-purple-700 align-middle">
                              Brief
                            </span>
                          )}
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
                  {hasMore && (
                    <div className="text-center mt-6">
                      <button
                        onClick={() => setVisibleCount(prev => prev + PAGE_SIZE)}
                        className="px-6 py-2.5 bg-neutral-100 hover:bg-neutral-200 text-neutral-700
                                   font-medium rounded-lg transition-colors text-sm"
                      >
                        Show more ({(filtered.length - visibleCount).toLocaleString()} remaining)
                      </button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </section>
    </div>
  )
}
