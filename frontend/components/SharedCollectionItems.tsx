'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { Calendar, ExternalLink, Tag, X } from 'lucide-react'
import { buildCanonicalUrl } from '@/lib/citationUrls'
import { groupDoctrines, hasDoctrine, type CaseTopic } from '@/lib/collectionTopics'

export interface SharedCase {
  id: string
  title: string
  decision_date: string | null
  reporter_cite: string | null
  court_name: string | null
  notes: string | null
  position: number
  topics?: CaseTopic[]
}

export interface SharedLegalText {
  item_id: number
  document_id: string
  slug: string
  title: string
  citation: string | null
  number: string | null
  notes: string | null
  position: number
}

interface Props {
  collectionId: string
  cases: SharedCase[]
  legalTexts: SharedLegalText[]
}

export default function SharedCollectionItems({ collectionId, cases, legalTexts }: Props) {
  const [doctrineId, setDoctrineId] = useState<string | null>(null)
  const groups = useMemo(() => groupDoctrines(cases), [cases])
  const selectedLabel = groups
    .flatMap(g => g.doctrines)
    .find(d => d.id === doctrineId)?.label

  const items = [
    ...cases
      .filter(c => !doctrineId || hasDoctrine(c, doctrineId))
      .map(c => ({ type: 'case' as const, key: `case-${c.id}`, position: c.position ?? 0, data: c })),
    // Statutes and rules carry no doctrine tags, so a topic filter hides them.
    ...(doctrineId ? [] : legalTexts).map(lt => ({
      type: 'legal_text' as const, key: `lt-${lt.item_id}`, position: lt.position ?? 0, data: lt,
    })),
  ].sort((a, b) => a.position - b.position)

  return (
    <div className="space-y-4">
      {groups.length > 0 && (
        <details open className="bg-white rounded-lg border border-stone-200 p-5 mb-2">
          <summary className="cursor-pointer font-semibold text-stone-900 flex items-center gap-2">
            <Tag className="h-4 w-4 text-sage-600" />
            Browse by topic
          </summary>
          <div className="mt-4 space-y-4">
            {groups.map(group => (
              <div key={group.topic}>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-500 mb-2">
                  {group.topic}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {group.doctrines.map(d => {
                    const selected = d.id === doctrineId
                    return (
                      <button
                        key={d.id}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => setDoctrineId(selected ? null : d.id)}
                        className={`text-sm px-2.5 py-1 rounded-full border transition ${
                          selected
                            ? 'bg-sage-700 border-sage-700 text-white'
                            : 'bg-white border-stone-200 text-stone-700 hover:border-sage-300 hover:bg-sage-50'
                        }`}
                      >
                        {d.label} <span className={selected ? 'text-sage-100' : 'text-stone-400'}>{d.count}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
            <p className="text-xs text-stone-400">
              Topic tags are assigned by AI from the case briefs and are still being reviewed.
            </p>
          </div>
        </details>
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-stone-900">
          {selectedLabel ? selectedLabel : 'Items in this Collection'}
        </h2>
        {doctrineId && (
          <button
            type="button"
            onClick={() => setDoctrineId(null)}
            className="flex items-center gap-1 text-sm text-sage-700 hover:text-sage-600"
          >
            <X className="h-4 w-4" />
            Show all {cases.length + legalTexts.length}
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <div className="text-center py-12 text-stone-500">
          <p>This collection is empty</p>
        </div>
      ) : (
        items.map(item => {
          if (item.type === 'case') {
            const caseItem = item.data as SharedCase
            return (
              <Link
                key={item.key}
                href={`${buildCanonicalUrl(caseItem.reporter_cite, caseItem.title)}?shared_collection=${collectionId}`}
                className="block bg-white rounded-lg border border-stone-200 p-5 hover:border-sage-200 hover:shadow-md transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs bg-sage-50 text-sage-700 px-2 py-0.5 rounded font-medium">
                        Case
                      </span>
                    </div>
                    <h3 className="font-semibold text-stone-900 text-lg hover:text-sage-600 transition">
                      {caseItem.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-stone-500">
                      {caseItem.court_name && (
                        <span>{caseItem.court_name}</span>
                      )}
                      {caseItem.decision_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(caseItem.decision_date).getFullYear()}
                        </span>
                      )}
                      {caseItem.reporter_cite && (
                        <span className="text-stone-400">{caseItem.reporter_cite}</span>
                      )}
                    </div>
                    {caseItem.topics && caseItem.topics.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {caseItem.topics.map(t => (
                          <span
                            key={t.id}
                            className={`text-xs px-2 py-0.5 rounded-full ${
                              t.is_primary
                                ? 'bg-sage-100 text-sage-800 font-medium'
                                : 'border border-stone-200 text-stone-600'
                            }`}
                          >
                            {t.label}
                          </span>
                        ))}
                      </div>
                    )}
                    {caseItem.notes && (
                      <p className="mt-3 text-sm text-stone-600 italic border-l-2 border-sage-200 pl-3 whitespace-pre-line">
                        {caseItem.notes}
                      </p>
                    )}
                  </div>
                  <ExternalLink className="h-5 w-5 text-stone-400 flex-shrink-0 ml-4" />
                </div>
              </Link>
            )
          }
          const lt = item.data as SharedLegalText
          const route = lt.document_id === 'frcp' ? '/rules'
            : lt.document_id === 'constitution' ? '/constitution'
            : '/statutes'
          const typeLabel = lt.document_id === 'frcp' ? 'FRCP'
            : lt.document_id === 'constitution' ? 'Constitution'
            : 'Statute'
          return (
            <Link
              key={item.key}
              href={`${route}/${lt.slug}`}
              className="block bg-white rounded-lg border border-stone-200 p-5 hover:border-sage-300 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs bg-sage-50 text-sage-700 px-2 py-0.5 rounded font-medium">
                      {typeLabel}
                    </span>
                  </div>
                  <h3 className="font-semibold text-stone-900 text-lg hover:text-sage-600 transition">
                    {lt.number ? `${typeLabel} ${lt.number}` : lt.title}
                    {lt.number && lt.title ? ` — ${lt.title}` : ''}
                  </h3>
                  {lt.citation && (
                    <p className="text-sm text-stone-400 mt-1">{lt.citation}</p>
                  )}
                  {lt.notes && (
                    <p className="mt-3 text-sm text-stone-600 italic border-l-2 border-sage-200 pl-3 whitespace-pre-line">
                      {lt.notes}
                    </p>
                  )}
                </div>
                <ExternalLink className="h-5 w-5 text-stone-400 flex-shrink-0 ml-4" />
              </div>
            </Link>
          )
        })
      )}
    </div>
  )
}
