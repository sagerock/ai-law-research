'use client'

import { useState, useCallback, useEffect } from 'react'
import { Plus, Trash2, List, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import type { MSJFact, MSJDocument } from '@/types'

interface MSJFactsEditorProps {
  facts: MSJFact[]
  documents: MSJDocument[]
  onChange: (facts: MSJFact[]) => void
}

// Normalize old single source_doc_id to new source_doc_ids array
function normalizeFact(fact: MSJFact): MSJFact {
  if (!fact.source_doc_ids) {
    return {
      ...fact,
      source_doc_ids: fact.source_doc_id ? [fact.source_doc_id] : [],
    }
  }
  return fact
}

export default function MSJFactsEditor({ facts, documents, onChange }: MSJFactsEditorProps) {
  const [localFacts, setLocalFacts] = useState<MSJFact[]>(
    facts.length > 0
      ? facts.map(normalizeFact)
      : [{ fact_number: 1, text: '', source_doc_ids: [], source_excerpt: null }]
  )
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null)
  const [expandedSources, setExpandedSources] = useState<number | null>(null)

  const debouncedSave = useCallback(
    (updated: MSJFact[]) => {
      if (saveTimeout) clearTimeout(saveTimeout)
      const timeout = setTimeout(() => {
        const nonEmpty = updated.filter((f) => f.text.trim())
        onChange(nonEmpty)
      }, 800)
      setSaveTimeout(timeout)
    },
    [onChange, saveTimeout]
  )

  useEffect(() => {
    return () => {
      if (saveTimeout) clearTimeout(saveTimeout)
    }
  }, [saveTimeout])

  const updateFact = (index: number, updates: Partial<MSJFact>) => {
    const updated = localFacts.map((f, i) => (i === index ? { ...f, ...updates } : f))
    setLocalFacts(updated)
    debouncedSave(updated)
  }

  const toggleSource = (factIndex: number, docId: number) => {
    const fact = localFacts[factIndex]
    const ids = fact.source_doc_ids || []
    const newIds = ids.includes(docId) ? ids.filter((id) => id !== docId) : [...ids, docId]
    updateFact(factIndex, { source_doc_ids: newIds })
  }

  const addFact = () => {
    const newFact: MSJFact = {
      fact_number: localFacts.length + 1,
      text: '',
      source_doc_ids: [],
      source_excerpt: null,
    }
    setLocalFacts([...localFacts, newFact])
  }

  const removeFact = (index: number) => {
    if (localFacts.length <= 1) return
    const updated = localFacts
      .filter((_, i) => i !== index)
      .map((f, i) => ({ ...f, fact_number: i + 1 }))
    setLocalFacts(updated)
    debouncedSave(updated)
  }

  const getDocTitle = (docId: number) => {
    const doc = documents.find((d) => d.id === docId)
    return doc ? doc.title : `Doc #${docId}`
  }

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
          <List className="h-5 w-5 text-sage-700" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-stone-900">Statement of Undisputed Material Facts</h2>
          <p className="text-sm text-stone-500">
            List each fact with references to supporting documents
          </p>
        </div>
      </div>

      {documents.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 text-xs text-amber-700">
          Upload your documents first (Step 2) so you can link facts to sources.
        </div>
      )}

      <div className="space-y-4">
        {localFacts.map((fact, index) => (
          <div key={index} className="flex gap-2 group">
            <div className="flex items-start pt-2.5">
              <span className="text-sm font-medium text-stone-400 w-6 text-right">
                {fact.fact_number}.
              </span>
            </div>

            <div className="flex-1 space-y-2">
              <textarea
                value={fact.text}
                onChange={(e) => updateFact(index, { text: e.target.value })}
                placeholder="Enter an undisputed material fact..."
                rows={2}
                className="w-full px-3 py-2 border border-stone-200 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent
                           resize-none"
              />

              {/* Source documents */}
              <div>
                <button
                  onClick={() => setExpandedSources(expandedSources === index ? null : index)}
                  className="flex items-center gap-1.5 text-xs text-stone-500 hover:text-sage-700 transition-colors"
                >
                  <FileText className="h-3 w-3" />
                  {(fact.source_doc_ids?.length || 0) === 0
                    ? 'Select source documents...'
                    : `${fact.source_doc_ids.length} source${fact.source_doc_ids.length !== 1 ? 's' : ''} selected`}
                  {expandedSources === index ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </button>

                {/* Selected sources as chips */}
                {fact.source_doc_ids?.length > 0 && expandedSources !== index && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {fact.source_doc_ids.map((docId) => (
                      <span
                        key={docId}
                        className="inline-flex items-center gap-1 px-2 py-0.5 bg-sage-50 text-sage-700
                                   rounded text-[11px] border border-sage-200"
                      >
                        {getDocTitle(docId)}
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded checkbox list */}
                {expandedSources === index && documents.length > 0 && (
                  <div className="mt-2 border border-stone-200 rounded-lg p-2 space-y-1 bg-stone-50">
                    {documents.map((doc) => (
                      <label
                        key={doc.id}
                        className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white
                                   cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={fact.source_doc_ids?.includes(doc.id) || false}
                          onChange={() => toggleSource(index, doc.id)}
                          className="rounded border-stone-300 text-sage-600 focus:ring-sage-500"
                        />
                        <span className="text-xs text-stone-700 truncate">
                          {doc.title}
                        </span>
                        <span className="text-[10px] text-stone-400 ml-auto flex-shrink-0">
                          {doc.doc_type}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Page/paragraph reference */}
              {(fact.source_doc_ids?.length || 0) > 0 && (
                <input
                  type="text"
                  value={fact.source_excerpt || ''}
                  onChange={(e) => updateFact(index, { source_excerpt: e.target.value })}
                  placeholder="Page/paragraph references (e.g., Hayes Dep. at 3; Downing Dep. at 5)"
                  className="w-full px-2 py-1 border border-stone-200 rounded text-xs
                             focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"
                />
              )}
            </div>

            <button
              onClick={() => removeFact(index)}
              className="p-1.5 mt-2 text-stone-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
              title="Remove fact"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={addFact}
        className="flex items-center gap-2 mt-4 px-3 py-2 text-sm text-sage-700 hover:bg-sage-50
                   rounded-lg transition-colors"
      >
        <Plus className="h-4 w-4" /> Add Fact
      </button>
    </div>
  )
}
