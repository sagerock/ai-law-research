'use client'

import { Case } from '@/types'
import CaseCard from './CaseCard'
import { Loader2 } from 'lucide-react'

interface CaseListProps {
  cases: Case[]
  isLoading: boolean
}

export default function CaseList({ cases, isLoading }: CaseListProps) {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-lg text-neutral-600">Searching cases...</span>
      </div>
    )
  }

  if (cases.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lg text-neutral-600">No cases found. Try a different search.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6 flex justify-between items-center">
        <h3 className="text-xl font-semibold text-neutral-900">
          Found {cases.length} relevant cases
        </h3>
        <div className="flex gap-2">
          <button className="px-3 py-1 text-sm border rounded-lg hover:bg-neutral-50">
            Sort by Relevance
          </button>
          <button className="px-3 py-1 text-sm border rounded-lg hover:bg-neutral-50">
            Filter
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {cases.map((caseItem, index) => (
          <CaseCard key={caseItem.id || index} case={caseItem} />
        ))}
      </div>
    </div>
  )
}