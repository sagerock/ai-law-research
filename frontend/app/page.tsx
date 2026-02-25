'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Scale, Search, MessageCircle, GraduationCap, BookOpen,
  ChevronDown, ThumbsUp, TrendingUp, Sparkles, GitFork,
  FileCheck, Heart, X, ArrowRight
} from 'lucide-react'
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
  const isSearchActive = query.trim().length > 0

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <header className="border-b border-stone-200/80 bg-cream/80 backdrop-blur-md sticky top-0 z-50 overflow-visible">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3.5">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 bg-sage-700 rounded-xl flex items-center justify-center
                              shadow-sm group-hover:bg-sage-600 transition-colors">
                <Scale className="h-[18px] w-[18px] text-white" />
              </div>
              <div className="hidden sm:block">
                <span className="font-display italic text-[22px] text-stone-900 leading-none">
                  Sage&apos;s
                </span>
                <span className="text-[13px] text-stone-500 block -mt-0.5 tracking-wide">
                  Study Group
                </span>
              </div>
            </Link>

            <nav className="flex items-center gap-1 sm:gap-2">
              <Link
                href="/study"
                className="px-3 py-2 text-sm text-stone-600 hover:text-stone-900 hover:bg-stone-100
                           rounded-lg transition-all flex items-center gap-1.5"
              >
                <GraduationCap className="h-4 w-4" />
                <span className="hidden sm:inline">Study</span>
              </Link>

              <div className="relative group">
                <button className="px-3 py-2 text-sm text-stone-600 hover:text-stone-900 hover:bg-stone-100
                                   rounded-lg transition-all flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4" />
                  <span className="hidden sm:inline">Reference</span>
                  <ChevronDown className="h-3 w-3 hidden sm:block" />
                </button>
                <div className="absolute right-0 top-full mt-1 w-56 bg-white border border-stone-200
                                rounded-xl shadow-lg shadow-stone-200/50 opacity-0 invisible
                                group-hover:opacity-100 group-hover:visible transition-all z-50 py-1.5">
                  <Link href="/rules" className="flex items-center gap-3 px-4 py-2.5 text-sm text-stone-700
                                                 hover:bg-sage-50 hover:text-sage-700 transition-colors">
                    Federal Rules (FRCP)
                  </Link>
                  <Link href="/constitution" className="flex items-center gap-3 px-4 py-2.5 text-sm text-stone-700
                                                        hover:bg-sage-50 hover:text-sage-700 transition-colors">
                    U.S. Constitution
                  </Link>
                  <Link href="/statutes" className="flex items-center gap-3 px-4 py-2.5 text-sm text-stone-700
                                                    hover:bg-sage-50 hover:text-sage-700 transition-colors">
                    Federal Statutes
                  </Link>
                </div>
              </div>

              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="px-2.5 py-2 text-stone-500 hover:text-stone-700 hover:bg-stone-100
                           rounded-lg transition-all"
                title="Discord"
              >
                <MessageCircle className="h-4 w-4" />
              </a>

              <div className="ml-1 pl-2 border-l border-stone-200">
                <UserMenu />
              </div>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className={`px-4 sm:px-6 transition-[padding] duration-300 ${isSearchActive ? 'pt-8 pb-4' : 'pt-20 pb-6'}`}>
        <div className="max-w-2xl mx-auto text-center">
          {/* Heading — hidden during search */}
          {!isSearchActive && (
            <div className="animate-fade-in-up mb-10">
              <h1 className="font-display text-[2.75rem] sm:text-6xl lg:text-7xl text-stone-900
                             tracking-tight leading-[1.08] mb-5">
                Case briefs,<br />
                <em className="text-sage-700">free forever.</em>
              </h1>
              <p className="text-lg sm:text-xl text-stone-500 max-w-md mx-auto leading-relaxed">
                AI-powered summaries for{' '}
                {caseCount ? caseCount.toLocaleString() : '...'}+ cases.
                <br className="hidden sm:block" />
                No subscription, no paywall.
              </p>
            </div>
          )}

          {/* Search */}
          <div className="relative max-w-xl mx-auto group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-stone-400
                               group-focus-within:text-sage-600 transition-colors" />
            <input
              type="text"
              value={query}
              onChange={e => handleQueryChange(e.target.value)}
              placeholder="Search by case name or citation..."
              autoFocus
              className="w-full pl-12 pr-12 py-4 bg-white border border-stone-200 rounded-2xl
                         text-base text-stone-900 placeholder:text-stone-400
                         focus:outline-none focus:ring-2 focus:ring-sage-200 focus:border-sage-400
                         shadow-sm hover:shadow-md hover:border-stone-300
                         transition-all duration-200"
            />
            {query && (
              <button
                onClick={() => handleQueryChange('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-1.5 text-stone-400
                           hover:text-stone-600 hover:bg-stone-100 rounded-full transition-all"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Feature pills */}
          {!isSearchActive && (
            <div className="flex flex-wrap justify-center gap-2.5 mt-8 animate-fade-in"
                 style={{ animationDelay: '200ms' }}>
              {[
                { icon: Sparkles, label: 'AI Briefs' },
                { icon: GitFork, label: 'Citation Network' },
                { icon: FileCheck, label: 'Brief Checker' },
                { icon: Heart, label: 'Free & Open' },
              ].map(({ icon: Icon, label }) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5
                             bg-sage-50 text-sage-700 rounded-full text-sm font-medium
                             border border-sage-100"
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Trending Cases */}
      {!isSearchActive && trendingCases.length > 0 && (
        <section className="px-4 sm:px-6 pb-20 pt-6">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-3 mb-6">
              <TrendingUp className="h-5 w-5 text-sage-600" />
              <h2 className="text-base font-semibold text-stone-800">Trending</h2>
              <div className="flex-1 h-px bg-stone-200" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {trendingCases.map((tc, i) => (
                <Link
                  key={tc.id}
                  href={`/case/${tc.id}`}
                  className="group bg-white border border-stone-200 rounded-xl p-5
                             hover:border-sage-300 hover:shadow-md hover:-translate-y-0.5
                             transition-all duration-200 animate-fade-in-up"
                  style={{ animationDelay: `${100 + i * 60}ms` }}
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <p className="font-medium text-stone-900 group-hover:text-sage-700
                                  transition-colors line-clamp-2 text-[15px] leading-snug flex-1">
                      {tc.title}
                    </p>
                    <ArrowRight className="h-4 w-4 text-stone-300 group-hover:text-sage-500
                                          shrink-0 mt-0.5 transition-all
                                          group-hover:translate-x-0.5" />
                  </div>
                  <div className="flex items-center gap-2 mb-3">
                    {tc.has_brief && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px]
                                       font-semibold bg-sage-50 text-sage-700 border border-sage-100">
                        <Sparkles className="h-2.5 w-2.5" />
                        Brief
                      </span>
                    )}
                    {tc.court_name && (
                      <span className="text-xs text-stone-400 truncate">{tc.court_name}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs text-stone-500">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1 text-stone-400">
                        <ThumbsUp className="h-3 w-3" /> {tc.thumbs_up}
                      </span>
                      <span className="flex items-center gap-1 text-stone-400">
                        <MessageCircle className="h-3 w-3" /> {tc.comment_count}
                      </span>
                    </div>
                    <span className="text-stone-400 font-mono text-[11px]">{tc.reporter_cite}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Search Results */}
      {(searched || searching) && (
        <section className="px-4 sm:px-6 pb-20">
          <div className="max-w-3xl mx-auto">
            {searching && !searched ? (
              <div className="text-center py-12">
                <div className="inline-flex items-center gap-2.5 text-stone-500">
                  <div className="h-4 w-4 border-2 border-sage-200 border-t-sage-600 rounded-full animate-spin" />
                  Searching...
                </div>
              </div>
            ) : searchResults.length === 0 && searched ? (
              <div className="text-center py-16">
                <div className="w-12 h-12 bg-stone-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Search className="h-5 w-5 text-stone-400" />
                </div>
                <p className="text-stone-600 text-lg font-medium">No cases match &ldquo;{query}&rdquo;</p>
                <p className="text-stone-400 text-sm mt-1.5">Try a shorter search or different spelling</p>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-sm text-stone-500">
                    {searchResults.length >= 50
                      ? '50+ cases found — refine your search'
                      : `${searchResults.length} case${searchResults.length === 1 ? '' : 's'} found`}
                  </span>
                  <div className="flex-1 h-px bg-stone-200" />
                </div>
                <div className="space-y-0.5">
                  {searchResults.map(c => (
                    <Link
                      key={c.id}
                      href={`/case/${c.id}`}
                      className="flex items-baseline justify-between gap-4 px-4 py-3 rounded-xl
                                 hover:bg-sage-50 transition-all group"
                    >
                      <div className="min-w-0">
                        <span className="font-medium text-stone-900 group-hover:text-sage-700 transition-colors">
                          {c.title}
                        </span>
                        {c.has_brief && (
                          <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px]
                                           font-semibold bg-sage-50 text-sage-700 border border-sage-100 align-middle">
                            Brief
                          </span>
                        )}
                        {c.court_name && (
                          <span className="text-stone-400 text-sm ml-2 hidden sm:inline">
                            &mdash; {c.court_name}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 shrink-0 text-sm">
                        <span className="hidden sm:inline text-stone-500 font-mono text-xs">{c.reporter_cite}</span>
                        <span className="text-stone-400">{year(c.decision_date)}</span>
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
