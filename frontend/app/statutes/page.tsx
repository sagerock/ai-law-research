'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Scale, Search, BookOpen, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import { UserMenu } from '@/components/auth/UserMenu'

interface StatuteItem {
  id: number
  slug: string
  title: string
  citation: string
  sort_order: number
}

interface SearchResult {
  slug: string
  title: string
  citation: string
  snippet: string
  document_id: string
}

export default function StatutesPage() {
  const [items, setItems] = useState<StatuteItem[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/legal-texts/federal_statutes`)
      .then(res => res.json())
      .then(data => {
        setItems(data.items || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const doSearch = useCallback((q: string) => {
    const trimmed = q.trim()
    if (trimmed.length < 2) {
      setSearchResults([])
      setSearching(false)
      return
    }
    setSearching(true)
    fetch(`${API_URL}/api/v1/legal-texts/search?q=${encodeURIComponent(trimmed)}&doc_id=federal_statutes&limit=30`)
      .then(res => res.json())
      .then(data => {
        setSearchResults(data.results || [])
        setSearching(false)
      })
      .catch(() => setSearching(false))
  }, [])

  const handleQueryChange = (value: string) => {
    setQuery(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!value.trim()) {
      setSearchResults([])
      setSearching(false)
      return
    }
    setSearching(true)
    debounceRef.current = setTimeout(() => doSearch(value), 300)
  }

  // Group statutes by title (e.g., "28 U.S.C.", "42 U.S.C.")
  const grouped: Record<string, StatuteItem[]> = {}
  for (const item of items) {
    // Extract title prefix from citation: "28 U.S.C. § 1332" -> "Title 28 U.S.C."
    const match = item.citation?.match(/^(\d+)\s+U\.S\.C\./)
    const group = match ? `Title ${match[1]} U.S.C.` : 'Other'
    if (!grouped[group]) grouped[group] = []
    grouped[group].push(item)
  }

  const showSearch = query.trim().length >= 2

  return (
    <div className="min-h-screen bg-cream">
      <header className="border-b bg-cream/80 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 bg-sage-700 rounded-xl flex items-center justify-center shadow-sm group-hover:bg-sage-600 transition-colors">
                <Scale className="h-[18px] w-[18px] text-white" />
              </div>
              <div className="hidden sm:block">
                <span className="font-display text-xl text-stone-900 leading-none">Law Study Group</span>
                <span className="text-[12px] text-stone-500 block mt-0.5 tracking-wide">Free Case Briefs for Law Students</span>
              </div>
            </Link>
            <UserMenu />
          </div>
        </div>
      </header>

      <section className="py-8 px-4">
        <div className="container mx-auto max-w-3xl">
          <Link href="/" className="inline-flex items-center text-sm text-stone-500 hover:text-stone-700 mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> Home
          </Link>

          <div className="flex items-center gap-3 mb-2">
            <BookOpen className="h-7 w-7 text-sage-600" />
            <h2 className="text-3xl font-bold text-stone-900">Federal Statutes</h2>
          </div>
          <p className="text-stone-600 mb-6">Browse {items.length || '...'} key federal statutes.</p>

          {/* Search */}
          <div className="relative max-w-xl mb-8">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-stone-400" />
            <input
              type="text"
              value={query}
              onChange={e => handleQueryChange(e.target.value)}
              placeholder="Search statutes..."
              className="w-full pl-12 pr-4 py-3 border-2 border-stone-200 rounded-xl
                         text-lg focus:border-sage-500 focus:outline-none transition-colors
                         bg-white shadow-sm"
            />
            {query && (
              <button
                onClick={() => handleQueryChange('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-stone-400
                           hover:text-stone-600 text-sm font-medium"
              >
                Clear
              </button>
            )}
          </div>

          {/* Search Results */}
          {showSearch && (
            <div className="mb-8">
              {searching ? (
                <p className="text-stone-500">Searching...</p>
              ) : searchResults.length === 0 ? (
                <p className="text-stone-500">No results found.</p>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-stone-500">{searchResults.length} results</p>
                  {searchResults.map(r => (
                    <Link
                      key={r.slug}
                      href={`/statutes/${r.slug}`}
                      className="block bg-white p-4 rounded-lg border border-stone-200
                                 hover:border-sage-300 transition-colors"
                    >
                      <h3 className="font-semibold text-stone-900">
                        {r.citation} &mdash; {r.title}
                      </h3>
                      <p
                        className="text-sm text-stone-600 mt-1 line-clamp-3"
                        dangerouslySetInnerHTML={{ __html: r.snippet }}
                      />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Full list grouped by title */}
          {!showSearch && (
            loading ? (
              <p className="text-stone-500">Loading statutes...</p>
            ) : (
              <div className="space-y-8">
                {Object.entries(grouped).map(([group, statutes]) => (
                  <div key={group}>
                    <h3 className="text-lg font-semibold text-stone-900 mb-3">{group}</h3>
                    <div className="space-y-1">
                      {statutes.map(item => (
                        <Link
                          key={item.slug}
                          href={`/statutes/${item.slug}`}
                          className="flex items-baseline gap-3 py-2.5 px-3 rounded-lg
                                     hover:bg-sage-50 transition-colors group"
                        >
                          <span className="text-sm text-sage-600 flex-shrink-0 whitespace-nowrap">
                            {item.citation}
                          </span>
                          <span className="text-stone-800 group-hover:text-sage-700 transition-colors">
                            {item.title}
                          </span>
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </section>
    </div>
  )
}
