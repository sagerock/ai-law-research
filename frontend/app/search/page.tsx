'use client'

import { useState } from 'react'
import SearchInterface from '@/components/SearchInterface'
import CaseList from '@/components/CaseList'
import { Case } from '@/types'
import Header from '@/components/Header'

export default function SearchPage() {
  const [searchResults, setSearchResults] = useState<Case[]>([])
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      {/* Hero Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto max-w-4xl text-center">
          <h2 className="text-4xl font-bold text-stone-900 mb-4">
            Advanced Case Search
          </h2>
          <p className="text-xl text-stone-600 mb-12">
            Search across all cases using keywords or natural language.
          </p>

          {/* Search Interface */}
          <SearchInterface
            onSearch={setSearchResults}
            setIsLoading={setIsLoading}
          />
        </div>
      </section>

      {/* Results Section */}
      {(searchResults.length > 0 || isLoading) && (
        <section className="py-8 px-4 bg-stone-50">
          <div className="container mx-auto max-w-6xl">
            <CaseList
              cases={searchResults}
              isLoading={isLoading}
            />
          </div>
        </section>
      )}
    </div>
  )
}
