'use client'

import { ArrowLeft, Copy, Check } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import SubsectionTree from '@/components/SubsectionTree'
import RelatedCases from '@/components/RelatedCases'
import Header from '@/components/Header'
import AddToCollectionDropdown from '@/components/AddToCollectionDropdown'

interface RuleData {
  id: number
  slug: string
  title: string
  number: string | null
  body: string
  content: {
    id: string
    number?: string
    title?: string
    text?: string
    subsections?: any[]
  }
}

export default function RuleDetailClient({ data }: { data: RuleData }) {
  const [copied, setCopied] = useState(false)
  const content = data.content

  const displayTitle = data.number
    ? `Rule ${data.number} — ${data.title}`
    : data.title

  const handleCopyAll = () => {
    navigator.clipboard.writeText(data.body).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      <section className="py-8 px-4">
        <div className="container mx-auto max-w-3xl">
          <Link href="/rules" className="inline-flex items-center text-sm text-stone-500 hover:text-stone-700 mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> All Rules
          </Link>

          <div className="bg-white rounded-xl border border-stone-200 p-6 sm:p-8">
            <div className="flex items-start justify-between gap-4 mb-6">
              <h2 className="text-2xl font-bold text-stone-900">{displayTitle}</h2>
              <div className="flex items-center gap-3 flex-shrink-0">
                <button
                  onClick={handleCopyAll}
                  className="flex items-center gap-1.5 text-sm text-stone-500
                             hover:text-stone-700 transition-colors"
                  title="Copy full text"
                >
                  {copied ? (
                    <><Check className="h-4 w-4 text-green-500" /> Copied</>
                  ) : (
                    <><Copy className="h-4 w-4" /> Copy</>
                  )}
                </button>
                <AddToCollectionDropdown itemType="legal_text" itemId={String(data.id)} />
              </div>
            </div>

            {/* Main text */}
            {content.text && (
              <p className="text-stone-800 leading-relaxed mb-4">{content.text}</p>
            )}

            {/* Subsections */}
            {content.subsections && content.subsections.length > 0 && (
              <SubsectionTree items={content.subsections} />
            )}
          </div>

          <RelatedCases docId="frcp" slug={data.slug} />
        </div>
      </section>
    </div>
  )
}
