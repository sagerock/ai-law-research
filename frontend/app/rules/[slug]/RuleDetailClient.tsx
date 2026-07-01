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

// Parse a flat rule string into an indented outline. Legal subdivisions follow
// the hierarchy (a) → (1) → (A) → (i), separated by blank lines in the source.
interface RuleBlock {
  marker: string | null
  text: string
  level: number
}

function isRoman(s: string): boolean {
  return /^[ivxlcdm]+$/.test(s)
}

// FRCP is numbered 1–86; FRE is 101–1103 — no overlap, so the rule number
// alone tells us which document a "rule-N" slug belongs to. Mirrors page.tsx.
function docForSlug(slug: string): 'fre' | 'frcp' {
  const m = slug.match(/rule-(\d+)/)
  const n = m ? parseInt(m[1], 10) : 0
  return n >= 101 ? 'fre' : 'frcp'
}

function parseOutline(text: string): RuleBlock[] {
  const blocks: RuleBlock[] = []
  let lastLevel = 0

  for (const raw of text.split(/\n\n+/)) {
    const para = raw.trim()
    if (!para) continue

    const match = para.match(/^\(([A-Za-z0-9]+)\)\s*/)
    if (!match) {
      // Continuation / intro text with no leading marker — indent to context.
      blocks.push({ marker: null, text: para, level: lastLevel })
      continue
    }

    const token = match[1]
    let level: number
    if (/^\d+$/.test(token)) {
      level = 1 // (1)
    } else if (/^[A-Z]+$/.test(token)) {
      level = 2 // (A)
    } else if (isRoman(token) && lastLevel >= 2) {
      level = 3 // (i) — only when nested under an (A)-level subdivision
    } else {
      level = 0 // (a)
    }

    lastLevel = level
    blocks.push({
      marker: `(${token})`,
      text: para.slice(match[0].length),
      level,
    })
  }

  return blocks
}

export default function RuleDetailClient({ data }: { data: RuleData }) {
  const [copied, setCopied] = useState(false)
  const content = data.content
  const outline = content.text ? parseOutline(content.text) : []

  const displayTitle = data.number
    ? `Rule ${data.number} — ${data.title}`
    : data.title

  // Point "back" at the index for this rule's own corpus: FRE rules live under
  // /evidence-rules, FRCP under /rules.
  const isFre = docForSlug(data.slug) === 'fre'
  const backHref = isFre ? '/evidence-rules' : '/rules'
  const backLabel = isFre ? 'All Evidence Rules' : 'All Rules'

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
          <Link href={backHref} className="inline-flex items-center text-sm text-stone-500 hover:text-stone-700 mb-4">
            <ArrowLeft className="h-4 w-4 mr-1" /> {backLabel}
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

            {/* Main text, rendered as an indented outline */}
            {outline.length > 0 && (
              <div className="space-y-3">
                {outline.map((block, i) => (
                  <p
                    key={i}
                    className="text-stone-800 leading-relaxed"
                    style={{ paddingLeft: `${block.level * 1.75}rem` }}
                  >
                    {block.marker && (
                      <span className="font-semibold text-stone-900 mr-1.5">
                        {block.marker}
                      </span>
                    )}
                    {block.text}
                  </p>
                ))}
              </div>
            )}

            {/* Subsections */}
            {content.subsections && content.subsections.length > 0 && (
              <SubsectionTree items={content.subsections} />
            )}
          </div>

          <RelatedCases docId={docForSlug(data.slug)} slug={data.slug} />
        </div>
      </section>
    </div>
  )
}
