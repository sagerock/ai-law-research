'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Search, ThumbsUp, TrendingUp, Sparkles, Link2,
  Heart, BarChart3, X, ArrowRight, MessageCircle
} from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import Header from '@/components/Header'
import { TortoiseMark } from '@/components/TortoiseMark'
import { BRAND_NAME, SITE_TAGLINE } from '@/lib/site'
import { buildCanonicalUrl } from '@/lib/citationUrls'

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
      <Header />

      {/* Hero */}
      <section className={`px-4 sm:px-6 transition-[padding] duration-300 ${isSearchActive ? 'pt-8 pb-4' : 'pt-20 pb-6'}`}>
        <div className="max-w-2xl mx-auto text-center">
          {/* Heading — hidden during search */}
          {!isSearchActive && (
            <div className="animate-fade-in-up mb-10">
              <div className="flex items-end justify-center gap-4 mb-4">
                <TortoiseMark className="w-14 h-10 sm:w-[68px] sm:h-[49px] mb-1.5" />
                <h1 className="font-display text-[3.25rem] sm:text-7xl font-semibold text-ink
                               tracking-tight leading-none">
                  {BRAND_NAME}
                </h1>
              </div>
              <p className="font-display text-lg sm:text-[21px] text-stone-500 max-w-lg mx-auto leading-relaxed">
                {SITE_TAGLINE}.
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
              placeholder={caseCount
                ? `Search ${caseCount.toLocaleString()}+ cases — try “Twombly” or a citation…`
                : 'Search by case name or citation…'}
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

          {/* Popular searches */}
          {!isSearchActive && (
            <div className="flex flex-wrap items-center justify-center gap-2.5 mt-6 animate-fade-in"
                 style={{ animationDelay: '200ms' }}>
              <span className="text-[13px] text-stone-500">Popular:</span>
              {[
                'Palsgraf v. Long Island R.R.',
                'Bell Atlantic v. Twombly',
                'Pennoyer v. Neff',
              ].map(name => (
                <button
                  key={name}
                  onClick={() => handleQueryChange(name)}
                  className="text-[13px] text-sage-700 bg-sage-100 hover:bg-sage-200
                             px-3 py-1.5 rounded-full transition-colors"
                >
                  {name}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Trust strip */}
      {!isSearchActive && (
        <section className="px-4 sm:px-6 py-12 bg-white border-y border-stone-200 mt-10">
          <div className="max-w-5xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-8">
            <div>
              <div className="w-10 h-10 rounded-xl bg-honey-100 flex items-center justify-center mb-3.5">
                <Link2 className="h-5 w-5 text-honey-600" />
              </div>
              <h3 className="font-display text-lg font-semibold text-ink mb-1.5">Sourced to the opinion</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                Every claim in a brief links to the{' '}
                <mark className="bg-honey-300 text-ink px-1 rounded-sm">exact passage</mark>{' '}
                in the court&rsquo;s opinion that supports it. Cite it the night before
                class with confidence.
              </p>
            </div>
            <div>
              <div className="w-10 h-10 rounded-xl bg-sage-100 flex items-center justify-center mb-3.5">
                <Heart className="h-5 w-5 text-sage-600" />
              </div>
              <h3 className="font-display text-lg font-semibold text-ink mb-1.5">Free forever</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                No paywall, no trial, no card. Read every brief without even making
                an account. The free alternative that stays free.
              </p>
            </div>
            <div>
              <div className="w-10 h-10 rounded-xl bg-sage-100 flex items-center justify-center mb-3.5">
                <BarChart3 className="h-5 w-5 text-sage-600" />
              </div>
              <h3 className="font-display text-lg font-semibold text-ink mb-1.5">Costs in the open</h3>
              <p className="text-sm text-stone-600 leading-relaxed">
                Runs on donations. We publish exactly what we spend on a public
                dashboard — and the surplus goes to charity.{' '}
                <Link href="/transparency" className="font-semibold text-sage-700 hover:text-honey-700 transition-colors">
                  See the numbers →
                </Link>
              </p>
            </div>
          </div>
        </section>
      )}

      {/* More than briefs */}
      {!isSearchActive && (
        <section className="px-4 sm:px-6 pt-12 pb-4 text-center">
          <div className="max-w-3xl mx-auto">
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-sage-700 mb-2">
              One free well, everything you draw from
            </div>
            <h2 className="font-display text-2xl font-semibold text-ink mb-6">More than briefs</h2>
            <div className="flex flex-wrap justify-center gap-2.5">
              {([
                ['Case briefs', '/'],
                ['Outlines', '/outlines'],
                ['Study tools', '/study'],
                ['Textbooks', '/textbooks'],
                ['Brief check', '/briefcheck'],
              ] as const).map(([label, href]) => (
                <Link
                  key={label}
                  href={href}
                  className="text-sm font-medium bg-white border border-stone-200 rounded-full
                             px-4.5 py-2 shadow-sm hover:border-sage-300 hover:text-sage-700 transition-colors"
                >
                  {label}
                </Link>
              ))}
              {['Practice hypos', 'Flashcards'].map(label => (
                <span
                  key={label}
                  className="inline-flex items-center gap-2 text-sm font-medium bg-honey-100
                             border border-honey-300 rounded-full px-4.5 py-2 text-stone-700"
                >
                  {label}
                  <span className="text-[10px] font-bold text-white bg-honey-600 px-1.5 py-0.5 rounded-full">
                    SOON
                  </span>
                </span>
              ))}
            </div>
          </div>
        </section>
      )}

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
                  href={buildCanonicalUrl(tc.reporter_cite, tc.title)}
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
                      href={buildCanonicalUrl(c.reporter_cite, c.title)}
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
