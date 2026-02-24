'use client'

import { Scale, ArrowLeft, Copy, Check } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import SubsectionTree from '@/components/SubsectionTree'
import RelatedCases from '@/components/RelatedCases'
import { UserMenu } from '@/components/auth/UserMenu'

interface StatuteData {
  slug: string
  title: string
  citation: string | null
  body: string
  content: {
    id: string
    citation?: string
    title?: string
    text?: string
    subsections?: any[]
  }
}

export default function StatuteDetailClient({ data }: { data: StatuteData }) {
  const [copied, setCopied] = useState(false)
  const content = data.content

  const displayTitle = data.citation
    ? `${data.citation} — ${data.title}`
    : data.title

  const handleCopyAll = () => {
    navigator.clipboard.writeText(data.body).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

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
          <Link href="/statutes" className="inline-flex items-center text-sm text-neutral-500 hover:text-neutral-700 mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> All Statutes
          </Link>

          <div className="bg-white rounded-xl border border-neutral-200 p-6 sm:p-8">
            <div className="flex items-start justify-between gap-4 mb-6">
              <h2 className="text-2xl font-bold text-neutral-900">{displayTitle}</h2>
              <button
                onClick={handleCopyAll}
                className="flex-shrink-0 flex items-center gap-1.5 text-sm text-neutral-500
                           hover:text-neutral-700 transition-colors"
                title="Copy full text"
              >
                {copied ? (
                  <><Check className="h-4 w-4 text-green-500" /> Copied</>
                ) : (
                  <><Copy className="h-4 w-4" /> Copy</>
                )}
              </button>
            </div>

            {/* Main text */}
            {content.text && (
              <p className="text-neutral-800 leading-relaxed mb-4 whitespace-pre-line">{content.text}</p>
            )}

            {/* Subsections */}
            {content.subsections && content.subsections.length > 0 && (
              <SubsectionTree items={content.subsections} />
            )}
          </div>

          <RelatedCases docId="federal_statutes" slug={data.slug} />
        </div>
      </section>
    </div>
  )
}
