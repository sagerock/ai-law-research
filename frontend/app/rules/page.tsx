'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Scale, Search, BookOpen, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import { UserMenu } from '@/components/auth/UserMenu'

interface RuleItem {
  id: number
  slug: string
  title: string
  number: string
  sort_order: number
}

interface SearchResult {
  slug: string
  title: string
  number: string
  snippet: string
  document_id: string
}

export default function RulesPage() {
  const [items, setItems] = useState<RuleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/legal-texts/frcp`)
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
    fetch(`${API_URL}/api/v1/legal-texts/search?q=${encodeURIComponent(trimmed)}&doc_id=frcp&limit=30`)
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

  const showSearch = query.trim().length >= 2

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Law Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free Case Briefs for Law Students</p>
              </div>
            </Link>
            <UserMenu />
          </div>
        </div>
      </header>

      <section className="py-8 px-4">
        <div className="container mx-auto max-w-3xl">
          <Link href="/" className="inline-flex items-center text-sm text-neutral-500 hover:text-neutral-700 mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> Home
          </Link>

          <div className="flex items-center gap-3 mb-2">
            <BookOpen className="h-7 w-7 text-purple-600" />
            <h2 className="text-3xl font-bold text-neutral-900">Federal Rules of Civil Procedure</h2>
          </div>
          <p className="text-neutral-600 mb-6">Browse and search all {items.length || '...'} rules.</p>

          {/* Search */}
          <div className="relative max-w-xl mb-8">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-neutral-400" />
            <input
              type="text"
              value={query}
              onChange={e => handleQueryChange(e.target.value)}
              placeholder="Search rules..."
              className="w-full pl-12 pr-4 py-3 border-2 border-neutral-200 rounded-xl
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

          {/* Search Results */}
          {showSearch && (
            <div className="mb-8">
              {searching ? (
                <p className="text-neutral-500">Searching...</p>
              ) : searchResults.length === 0 ? (
                <p className="text-neutral-500">No results found.</p>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-neutral-500">{searchResults.length} results</p>
                  {searchResults.map(r => (
                    <Link
                      key={r.slug}
                      href={`/rules/${r.slug}`}
                      className="block bg-white p-4 rounded-lg border border-neutral-200
                                 hover:border-purple-400 transition-colors"
                    >
                      <h3 className="font-semibold text-neutral-900">
                        Rule {r.number} &mdash; {r.title}
                      </h3>
                      <p
                        className="text-sm text-neutral-600 mt-1 line-clamp-3"
                        dangerouslySetInnerHTML={{ __html: r.snippet }}
                      />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Full list */}
          {!showSearch && (
            loading ? (
              <p className="text-neutral-500">Loading rules...</p>
            ) : (
              <div className="space-y-1">
                {items.map(item => (
                  <Link
                    key={item.slug}
                    href={`/rules/${item.slug}`}
                    className="flex items-baseline gap-3 py-2.5 px-3 rounded-lg
                               hover:bg-purple-50 transition-colors group"
                  >
                    <span className="text-sm font-mono text-purple-600 w-12 flex-shrink-0 text-right">
                      {item.number}
                    </span>
                    <span className="text-neutral-800 group-hover:text-purple-700 transition-colors">
                      {item.title}
                    </span>
                  </Link>
                ))}
              </div>
            )
          )}
        </div>
      </section>
    </div>
  )
}
