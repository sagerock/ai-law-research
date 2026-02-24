'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Scale, BookOpen, Search, MessageCircle, GraduationCap, TrendingUp, ThumbsUp, ChevronDown } from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import { UserMenu } from '@/components/auth/UserMenu'

interface SearchCase {
  id: string
  title: string
  reporter_cite: string
  decision_date: string | null
  court_name: string | null
  has_brief: boolean
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

export default function HomePage() {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchCase[]>([])
  const [searching, setSearching] = useState(false)
  const [searched, setSearched] = useState(false)
  const [caseCount, setCaseCount] = useState<number | null>(null)
  const [trendingCases, setTrendingCases] = useState<TrendingCase[]>([])
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch case count + trending on mount
  useEffect(() => {
    fetch(`${API_URL}/api/v1/case-count`)
      .then(res => res.json())
      .then(data => setCaseCount(data.count ?? null))
      .catch(() => {})

    fetch(`${API_URL}/api/v1/trending-cases`)
      .then(res => res.json())
      .then(data => setTrendingCases(data.cases || []))
      .catch(() => {})
  }, [])

  // Debounced search
  const doSearch = useCallback((q: string) => {
    const trimmed = q.trim()
    if (trimmed.length < 2) {
      setSearchResults([])
      setSearched(false)
      setSearching(false)
      return
    }
    setSearching(true)
    fetch(`${API_URL}/api/v1/search-cases?q=${encodeURIComponent(trimmed)}&limit=50`)
      .then(res => res.json())
      .then(data => {
        setSearchResults(data.cases || [])
        setSearched(true)
        setSearching(false)
      })
      .catch(() => {
        setSearching(false)
        setSearched(true)
      })
  }, [])

  const handleQueryChange = (value: string) => {
    setQuery(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!value.trim()) {
      setSearchResults([])
      setSearched(false)
      setSearching(false)
      return
    }
    setSearching(true)
    debounceRef.current = setTimeout(() => doSearch(value), 300)
  }

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
              <div className="relative group">
                <button className="text-neutral-600 hover:text-neutral-900 transition flex items-center">
                  <BookOpen className="h-5 w-5 sm:mr-1" />
                  <span className="hidden sm:inline">Reference</span>
                  <ChevronDown className="h-3.5 w-3.5 ml-0.5 hidden sm:block" />
                </button>
                <div className="absolute right-0 top-full mt-1 w-52 bg-white border border-neutral-200
                                rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100
                                group-hover:visible transition-all z-50">
                  <Link href="/rules" className="block px-4 py-2.5 text-sm text-neutral-700 hover:bg-purple-50 hover:text-purple-700 rounded-t-lg">
                    Federal Rules (FRCP)
                  </Link>
                  <Link href="/constitution" className="block px-4 py-2.5 text-sm text-neutral-700 hover:bg-purple-50 hover:text-purple-700">
                    U.S. Constitution
                  </Link>
                  <Link href="/statutes" className="block px-4 py-2.5 text-sm text-neutral-700 hover:bg-purple-50 hover:text-purple-700 rounded-b-lg">
                    Federal Statutes
                  </Link>
                </div>
              </div>
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
            <h2 className="text-3xl font-bold text-neutral-900">Case Search</h2>
          </div>
          <p className="text-neutral-600 mb-8">
            Search {caseCount ? caseCount.toLocaleString() : '...'} cases by name or citation.
          </p>

          {/* Search input */}
          <div className="relative max-w-xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-neutral-400" />
            <input
              type="text"
              value={query}
              onChange={e => handleQueryChange(e.target.value)}
              placeholder="Search cases by name or citation..."
              autoFocus
              className="w-full pl-12 pr-4 py-3.5 border-2 border-neutral-200 rounded-xl
                         text-lg focus:border-purple-500 focus:outline-none transition-colors
                         bg-white shadow-sm"
            />
            {query && (
              <button
                onClick={() => handleQueryChange('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400
                           hover:text-neutral-600 text-sm font-medium"
              >
                Clear
              </button>
            )}
          </div>
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

      {/* Search Results */}
      {(searched || searching) && (
        <section className="px-4 pb-16">
          <div className="container mx-auto max-w-3xl">
            {searching && !searched ? (
              <div className="text-center py-8 text-neutral-500">Searching...</div>
            ) : searchResults.length === 0 && searched ? (
              <div className="text-center py-12">
                <p className="text-neutral-500 text-lg">No cases match &ldquo;{query}&rdquo;</p>
                <p className="text-neutral-400 text-sm mt-2">Try a shorter search or different spelling</p>
              </div>
            ) : (
              <>
                <div className="text-sm text-neutral-500 mb-3">
                  {searchResults.length >= 50
                    ? '50+ cases found — refine your search for better results'
                    : `${searchResults.length} case${searchResults.length === 1 ? '' : 's'} found`}
                </div>
                <div className="space-y-1">
                  {searchResults.map(c => (
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
              </>
            )}
          </div>
        </section>
      )}
    </div>
  )
}
