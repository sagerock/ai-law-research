'use client'

import { Case } from '@/types'
import { Calendar, FileText, TrendingUp, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import Link from 'next/link'

interface CaseCardProps {
  case: Case
}

export default function CaseCard({ case: caseItem }: CaseCardProps) {
  const getCitatorBadge = (badge?: string) => {
    switch (badge) {
      case 'green':
        return (
          <div className="flex items-center text-green-600">
            <CheckCircle className="h-4 w-4 mr-1" />
            Good Law
          </div>
        )
      case 'yellow':
        return (
          <div className="flex items-center text-yellow-600">
            <AlertCircle className="h-4 w-4 mr-1" />
            Caution
          </div>
        )
      case 'red':
        return (
          <div className="flex items-center text-red-600">
            <XCircle className="h-4 w-4 mr-1" />
            Negative
          </div>
        )
      default:
        return null
    }
  }

  // Extract court name from metadata if not available at top level
  const getCourtName = () => {
    if (caseItem.court_name) return caseItem.court_name
    if (caseItem.metadata?.court) return caseItem.metadata.court
    if (caseItem.metadata?.court_citation_string) return caseItem.metadata.court_citation_string
    return null
  }

  const courtName = getCourtName()

  return (
    <Link href={`/case/${caseItem.id}`} className="block">
      <div className="bg-white p-6 rounded-lg border border-neutral-200 hover:border-blue-300 hover:shadow-md transition cursor-pointer">
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1">
            <h4 className="text-lg font-semibold text-neutral-900 hover:text-blue-600 transition">
              {caseItem.title || caseItem.case_name || 'Untitled Case'}
            </h4>
            <div className="flex items-center gap-4 mt-2 text-sm text-neutral-600">
              {courtName && (
                <span className="flex items-center">
                  <FileText className="h-3 w-3 mr-1" />
                  {courtName}
                </span>
              )}
              {(caseItem.date_filed || caseItem.decision_date) && (
                <span className="flex items-center">
                  <Calendar className="h-3 w-3 mr-1" />
                  {caseItem.date_filed || caseItem.decision_date}
                </span>
              )}
              {caseItem.citation_count !== undefined && (
                <span className="flex items-center">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  {caseItem.citation_count} citations
                </span>
              )}
            </div>
          </div>
          {getCitatorBadge(caseItem.citator_badge)}
        </div>

        {/* Snippet or Content Preview */}
        {(caseItem.snippet || caseItem.content) && (
          <p
            className="text-sm text-neutral-700 line-clamp-3 mb-3"
            dangerouslySetInnerHTML={{
              __html: (caseItem.snippet || caseItem.content || '').replace(
                /<em>/g, '<em class="font-semibold text-blue-700 not-italic bg-blue-50 px-1 rounded">'
              )
            }}
          />
        )}

        {/* Match Score */}
        {(caseItem.similarity !== undefined || caseItem.score !== undefined) && (
          <div className="flex items-center gap-4">
            {caseItem.similarity !== undefined && (
              <div className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                AI Match: {(caseItem.similarity * 100).toFixed(1)}%
              </div>
            )}
            {caseItem.score !== undefined && (
              <div className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded">
                Keyword Score: {caseItem.score.toFixed(1)}
              </div>
            )}
          </div>
        )}

        {/* Citations if available */}
        {caseItem.citations && caseItem.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-neutral-100">
            <p className="text-xs text-neutral-600">
              Citations: {caseItem.citations.slice(0, 2).join(' • ')}
              {caseItem.citations.length > 2 && ` • +${caseItem.citations.length - 2} more`}
            </p>
          </div>
        )}
      </div>
    </Link>
  )
}