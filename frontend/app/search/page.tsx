'use client'

import { useState } from 'react'
import { Scale, Brain, Upload, BookOpen, TrendingUp, Heart } from 'lucide-react'
import SearchInterface from '@/components/SearchInterface'
import CaseList from '@/components/CaseList'
import { Case } from '@/types'
import Link from 'next/link'
import { UserMenu } from '@/components/auth/UserMenu'

export default function SearchPage() {
  const [searchResults, setSearchResults] = useState<Case[]>([])
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50 overflow-visible">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Sage's Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
              </div>
            </Link>
            <nav className="flex items-center space-x-4 sm:space-x-6">
              <Link
                href="/"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <BookOpen className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Casebook</span>
              </Link>
              <Link
                href="/transparency"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <Heart className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Transparency</span>
              </Link>
              <UserMenu />
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto max-w-4xl text-center">
          <h2 className="text-4xl font-bold text-neutral-900 mb-4">
            Advanced Case Search
          </h2>
          <p className="text-xl text-neutral-600 mb-12">
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
        <section className="py-8 px-4 bg-neutral-50">
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
