'use client'

import { useState } from 'react'
import { Search, Sparkles, Hash } from 'lucide-react'
import { Case, SearchRequest } from '@/types'

interface SearchInterfaceProps {
  onSearch: (results: Case[]) => void
  setIsLoading: (loading: boolean) => void
}

export default function SearchInterface({ onSearch, setIsLoading }: SearchInterfaceProps) {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'semantic' | 'keyword' | 'hybrid'>('hybrid')

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsLoading(true)

    try {
      const searchRequest: SearchRequest = {
        query: query.trim(),
        search_type: searchType,
        limit: 20
      }

      // For now, use mock data - replace with actual API call
      const response = await fetch('http://localhost:8000/api/v1/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchRequest)
      })

      if (response.ok) {
        const data = await response.json()
        onSearch(data.results || [])
      } else {
        // Fallback to mock data for testing
        const mockResults: Case[] = [
          {
            id: '1',
            case_name: 'State v. One or More Persons Over Whom Court\'s Jurisdiction',
            court_name: 'Connecticut Appellate Court',
            date_filed: '2008-05-20',
            citation_count: 8,
            snippet: 'Personal jurisdiction requires minimum contacts with the forum state...',
            similarity: 0.95,
            citator_badge: 'green'
          },
          {
            id: '2',
            case_name: 'Buckley v. American Constitutional Law Foundation',
            court_name: 'Supreme Court',
            date_filed: '1999-01-12',
            citation_count: 521,
            snippet: 'Constitutional law principles regarding freedom of speech...',
            similarity: 0.89,
            citator_badge: 'yellow'
          }
        ]
        onSearch(mockResults)
      }
    } catch (error) {
      console.error('Search error:', error)
      // Use mock data as fallback
      const mockResults: Case[] = [
        {
          id: '1',
          case_name: 'Sample Case for Testing',
          court_name: 'Test Court',
          date_filed: '2024-01-01',
          citation_count: 10,
          snippet: 'This is a test case result...',
          similarity: 0.85
        }
      ]
      onSearch(mockResults)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSearch} className="w-full max-w-3xl mx-auto">
      <div className="flex flex-col gap-4">
        {/* Search Type Selector */}
        <div className="flex justify-center gap-2">
          <button
            type="button"
            onClick={() => setSearchType('hybrid')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
              searchType === 'hybrid'
                ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                : 'bg-white text-neutral-600 border-2 border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <Search className="h-4 w-4" />
            <Sparkles className="h-4 w-4" />
            Hybrid Search
          </button>
          <button
            type="button"
            onClick={() => setSearchType('semantic')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
              searchType === 'semantic'
                ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                : 'bg-white text-neutral-600 border-2 border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <Sparkles className="h-4 w-4" />
            AI Search
          </button>
          <button
            type="button"
            onClick={() => setSearchType('keyword')}
            className={`px-4 py-2 rounded-lg flex items-center gap-2 transition ${
              searchType === 'keyword'
                ? 'bg-blue-100 text-blue-700 border-2 border-blue-300'
                : 'bg-white text-neutral-600 border-2 border-neutral-200 hover:border-neutral-300'
            }`}
          >
            <Hash className="h-4 w-4" />
            Keyword Only
          </button>
        </div>

        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              searchType === 'semantic'
                ? "Describe your legal issue in natural language..."
                : searchType === 'keyword'
                ? "Enter exact keywords..."
                : "Search cases by keyword or concept..."
            }
            className="w-full px-6 py-4 pr-14 text-lg border-2 border-neutral-200 rounded-xl focus:outline-none focus:border-blue-500 transition"
          />
          <button
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            <Search className="h-5 w-5" />
          </button>
        </div>

        {/* Search Tips */}
        <div className="text-sm text-neutral-600 text-center">
          {searchType === 'semantic' && (
            <p>💡 Try: "Cases about employer liability for remote worker injuries"</p>
          )}
          {searchType === 'keyword' && (
            <p>💡 Use quotes for exact phrases: "personal jurisdiction"</p>
          )}
          {searchType === 'hybrid' && (
            <p>💡 Best of both: AI understanding + exact keyword matching</p>
          )}
        </div>
      </div>
    </form>
  )
}