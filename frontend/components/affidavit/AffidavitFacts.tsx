'use client'

import { useState, useEffect, useCallback } from 'react'
import { List, Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react'
import type { AffidavitFact, ToolDocument } from '@/types'

interface AffidavitFactsProps {
  facts: AffidavitFact[]
  documents: ToolDocument[]
  onChange: (facts: AffidavitFact[]) => void
}

const KNOWLEDGE_BASES = [
  { value: 'personal_observation', label: 'Personal Observation' },
  { value: 'business_records', label: 'Business Records' },
  { value: 'official_records', label: 'Official Records' },
  { value: 'participation', label: 'Direct Participation' },
  { value: 'other', label: 'Other' },
]

export default function AffidavitFacts({ facts, documents, onChange }: AffidavitFactsProps) {
  const [localFacts, setLocalFacts] = useState<AffidavitFact[]>(facts.length > 0 ? facts : [])
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null)
  const [expandedDocs, setExpandedDocs] = useState<Record<number, boolean>>({})

  const debouncedSave = useCallback(
    (updated: AffidavitFact[]) => {
      if (saveTimeout) clearTimeout(saveTimeout)
      const timeout = setTimeout(() => onChange(updated), 800)
      setSaveTimeout(timeout)
    },
    [onChange, saveTimeout]
  )

  useEffect(() => {
    return () => { if (saveTimeout) clearTimeout(saveTimeout) }
  }, [saveTimeout])

  const addFact = () => {
    const newFact: AffidavitFact = {
      fact_number: localFacts.length + 1,
      text: '',
      source_doc_ids: [],
      knowledge_basis: 'personal_observation',
    }
    const updated = [...localFacts, newFact]
    setLocalFacts(updated)
    debouncedSave(updated)
  }

  const updateFact = (index: number, field: keyof AffidavitFact, value: any) => {
    const updated = localFacts.map((f, i) =>
      i === index ? { ...f, [field]: value } : f
    )
    setLocalFacts(updated)
    debouncedSave(updated)
  }

  const removeFact = (index: number) => {
    const updated = localFacts
      .filter((_, i) => i !== index)
      .map((f, i) => ({ ...f, fact_number: i + 1 }))
    setLocalFacts(updated)
    debouncedSave(updated)
  }

  const toggleDocSource = (factIndex: number, docId: number) => {
    const fact = localFacts[factIndex]
    const ids = fact.source_doc_ids || []
    const updated = ids.includes(docId)
      ? ids.filter((id) => id !== docId)
      : [...ids, docId]
    updateFact(factIndex, 'source_doc_ids', updated)
  }

  const inputClass = "w-full px-3 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
          <List className="h-5 w-5 text-sage-700" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-stone-900">Facts Affiant Can Attest To</h2>
          <p className="text-sm text-stone-500">List facts the affiant can attest to from personal knowledge. Related facts will be grouped by topic.</p>
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4 mt-3">
        <p className="text-xs text-amber-700">
          All facts must be based on personal knowledge. No hearsay, no legal conclusions. Related facts on the same topic can be combined into one entry.
        </p>
      </div>

      <div className="space-y-4">
        {localFacts.map((fact, index) => (
          <div key={index} className="border border-stone-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-stone-700">Paragraph {fact.fact_number}</span>
              <button
                onClick={() => removeFact(index)}
                className="p-1 text-stone-400 hover:text-red-500 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>

            <textarea
              value={fact.text}
              onChange={(e) => updateFact(index, 'text', e.target.value)}
              placeholder="State one specific fact the affiant personally knows. e.g., 'I was present at the intersection of Main Street and Oak Avenue on March 5, 2024, at approximately 3:00 p.m.'"
              rows={3}
              className={inputClass + ' resize-none mb-3'}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-stone-600 mb-1">Knowledge Basis</label>
                <select
                  value={fact.knowledge_basis}
                  onChange={(e) => updateFact(index, 'knowledge_basis', e.target.value)}
                  className={inputClass}
                >
                  {KNOWLEDGE_BASES.map((b) => (
                    <option key={b.value} value={b.value}>{b.label}</option>
                  ))}
                </select>
              </div>

              {fact.knowledge_basis === 'other' && (
                <div>
                  <label className="block text-xs font-medium text-stone-600 mb-1">Specify basis</label>
                  <input
                    type="text"
                    value={fact.knowledge_basis_detail || ''}
                    onChange={(e) => updateFact(index, 'knowledge_basis_detail', e.target.value)}
                    placeholder="How does the affiant know this?"
                    className={inputClass}
                  />
                </div>
              )}
            </div>

            {/* Source document linking */}
            {documents.length > 0 && (
              <div className="mt-3">
                <button
                  onClick={() => setExpandedDocs({ ...expandedDocs, [index]: !expandedDocs[index] })}
                  className="flex items-center gap-1 text-xs text-stone-500 hover:text-stone-700"
                >
                  {expandedDocs[index] ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  Source Documents ({(fact.source_doc_ids || []).length} selected)
                </button>
                {expandedDocs[index] && (
                  <div className="mt-2 space-y-1 pl-4">
                    {documents.map((doc) => (
                      <label key={doc.id} className="flex items-center gap-2 text-xs text-stone-600 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={(fact.source_doc_ids || []).includes(doc.id)}
                          onChange={() => toggleDocSource(index, doc.id)}
                          className="h-3.5 w-3.5 rounded border-stone-300 text-sage-600 focus:ring-sage-500"
                        />
                        {doc.title} ({doc.doc_type})
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        <button
          onClick={addFact}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed
                     border-stone-200 rounded-lg text-sm text-stone-500 hover:border-sage-300
                     hover:text-sage-700 transition-colors"
        >
          <Plus className="h-4 w-4" /> Add Fact
        </button>
      </div>
    </div>
  )
}
