'use client'

import { useState } from 'react'
import { Scale, MessageCircle, GraduationCap } from 'lucide-react'
import SearchInterface from '@/components/SearchInterface'
import CaseList from '@/components/CaseList'
import { Case } from '@/types'
import Link from 'next/link'
import { UserMenu } from '@/components/auth/UserMenu'

export default function SearchPage() {
  const [searchResults, setSearchResults] = useState<Case[]>([])
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <header className="border-b bg-cream/80 backdrop-blur-md sticky top-0 z-50 overflow-visible">
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
            <nav className="flex items-center space-x-4 sm:space-x-6">
              <Link
                href="/study"
                className="text-stone-600 hover:text-stone-900 transition flex items-center"
              >
                <GraduationCap className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Study</span>
              </Link>
              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="text-stone-600 hover:text-stone-900 transition flex items-center"
                title="Discord"
              >
                <MessageCircle className="h-5 w-5" />
              </a>
              <UserMenu />
            </nav>
          </div>
        </div>
      </header>

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
