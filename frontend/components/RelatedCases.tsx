'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { FileText, Calendar, TrendingUp } from 'lucide-react'
import { API_URL } from '@/lib/api'

interface RelatedCase {
  id: string
  title: string
  court_name: string | null
  year: string
  citation_count: number
  snippet: string
}

export default function RelatedCases({ docId, slug }: { docId: string; slug: string }) {
  const [cases, setCases] = useState<RelatedCase[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/legal-texts/${docId}/${slug}/cases`)
      .then(res => res.ok ? res.json() : { results: [] })
      .then(data => setCases(data.results || []))
      .catch(() => setCases([]))
      .finally(() => setLoading(false))
  }, [docId, slug])

  if (loading || cases.length === 0) return null

  return (
    <div className="mt-8">
      <h3 className="text-lg font-semibold text-stone-900 mb-4">Cases Citing This Provision</h3>
      <div className="space-y-3">
        {cases.map(c => (
          <Link key={c.id} href={`/case/${c.id}`} className="block">
            <div className="bg-white p-4 rounded-lg border border-stone-200 hover:border-sage-200 hover:shadow-md transition">
              <h4 className="font-semibold text-stone-900 hover:text-sage-600 transition text-sm">
                {c.title}
              </h4>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-stone-500">
                {c.court_name && (
                  <span className="flex items-center">
                    <FileText className="h-3 w-3 mr-1" />
                    {c.court_name}
                  </span>
                )}
                {c.year && (
                  <span className="flex items-center">
                    <Calendar className="h-3 w-3 mr-1" />
                    {c.year}
                  </span>
                )}
                {c.citation_count > 0 && (
                  <span className="flex items-center">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    {c.citation_count} citations
                  </span>
                )}
              </div>
              {c.snippet && (
                <p
                  className="text-xs text-stone-600 mt-2 line-clamp-2"
                  dangerouslySetInnerHTML={{
                    __html: c.snippet.replace(
                      /<em>/g,
                      '<em class="font-semibold text-sage-700 not-italic bg-sage-50 px-0.5 rounded">'
                    )
                  }}
                />
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
