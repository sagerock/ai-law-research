'use client'

import { useState } from 'react'
import { Scale, Brain, Upload, BookOpen, TrendingUp } from 'lucide-react'
import SearchInterface from '@/components/SearchInterface'
import CaseList from '@/components/CaseList'
import { Case } from '@/types'
import Link from 'next/link'
import { UserMenu } from '@/components/auth/UserMenu'

export default function HomePage() {
  const [searchResults, setSearchResults] = useState<Case[]>([])
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50 overflow-visible">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">LegalSearch</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">AI-Powered Legal Research</p>
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
              <button className="text-neutral-600 hover:text-neutral-900 transition hidden sm:flex items-center">
                <BookOpen className="h-5 w-5 mr-2" />
                My Library
              </button>
              <UserMenu />
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-16 px-4">
        <div className="container mx-auto max-w-4xl text-center">
          <h2 className="text-4xl font-bold text-neutral-900 mb-4">
            Find Cases Faster with AI
          </h2>
          <p className="text-xl text-neutral-600 mb-12">
            Search millions of cases using keywords or natural language.
            Our AI understands legal concepts, not just exact matches.
          </p>

          {/* Search Interface */}
          <SearchInterface
            onSearch={setSearchResults}
            setIsLoading={setIsLoading}
          />

          {/* Feature Pills */}
          <div className="flex justify-center gap-4 mt-8">
            <div className="flex items-center px-4 py-2 bg-blue-50 text-blue-700 rounded-full text-sm">
              <Brain className="h-4 w-4 mr-2" />
              Semantic Search
            </div>
            <div className="flex items-center px-4 py-2 bg-green-50 text-green-700 rounded-full text-sm">
              <TrendingUp className="h-4 w-4 mr-2" />
              Citation Analysis
            </div>
            <div className="flex items-center px-4 py-2 bg-purple-50 text-purple-700 rounded-full text-sm">
              <Scale className="h-4 w-4 mr-2" />
              100+ Cases Indexed
            </div>
          </div>
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

      {/* Stats Section */}
      {!isLoading && searchResults.length === 0 && (
        <section className="py-16 px-4">
          <div className="container mx-auto max-w-4xl">
            <div className="grid md:grid-cols-3 gap-8 text-center">
              <div>
                <div className="text-3xl font-bold text-neutral-900">100+</div>
                <div className="text-neutral-600">Cases Indexed</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-neutral-900">20</div>
                <div className="text-neutral-600">Courts Covered</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-neutral-900">AI</div>
                <div className="text-neutral-600">Semantic Understanding</div>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
