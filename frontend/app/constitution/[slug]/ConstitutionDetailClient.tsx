'use client'

import { Scale, ArrowLeft, Copy, Check } from 'lucide-react'
import Link from 'next/link'
import { useState } from 'react'
import SubsectionTree from '@/components/SubsectionTree'
import RelatedCases from '@/components/RelatedCases'
import { UserMenu } from '@/components/auth/UserMenu'

interface ConstitutionData {
  slug: string
  title: string
  number: string | null
  body: string
  content: {
    id: string
    title?: string
    text?: string
    sections?: any[]
    subsections?: any[]
  }
}

export default function ConstitutionDetailClient({ data }: { data: ConstitutionData }) {
  const [copied, setCopied] = useState(false)
  const content = data.content

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
          <Link href="/constitution" className="inline-flex items-center text-sm text-neutral-500 hover:text-neutral-700 mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> U.S. Constitution
          </Link>

          <div className="bg-white rounded-xl border border-neutral-200 p-6 sm:p-8">
            <div className="flex items-start justify-between gap-4 mb-6">
              <h2 className="text-2xl font-bold text-neutral-900">{data.title}</h2>
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

            {/* Main text (for amendments without sections) */}
            {content.text && (
              <p className="text-neutral-800 leading-relaxed mb-4">{content.text}</p>
            )}

            {/* Sections (for articles) */}
            {content.sections && content.sections.length > 0 && (
              <div className="space-y-6">
                {content.sections.map((section: any) => (
                  <div key={section.id} className="border-t border-neutral-100 pt-4 first:border-0 first:pt-0">
                    <h3 className="font-semibold text-neutral-900 mb-2">{section.title}</h3>
                    {section.text && (
                      <p className="text-neutral-800 leading-relaxed">{section.text}</p>
                    )}
                    {section.subsections && section.subsections.length > 0 && (
                      <div className="mt-2">
                        <SubsectionTree items={section.subsections} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Subsections (for amendments with sections) */}
            {content.subsections && content.subsections.length > 0 && (
              <SubsectionTree items={content.subsections} />
            )}
          </div>

          <RelatedCases docId="constitution" slug={data.slug} />
        </div>
      </section>
    </div>
  )
}
