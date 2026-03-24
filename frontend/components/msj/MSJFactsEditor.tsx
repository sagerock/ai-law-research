'use client'

import { useState, useCallback, useEffect } from 'react'
import { Plus, Trash2, List, GripVertical } from 'lucide-react'
import type { MSJFact, MSJDocument } from '@/types'

interface MSJFactsEditorProps {
  facts: MSJFact[]
  documents: MSJDocument[]
  onChange: (facts: MSJFact[]) => void
}

export default function MSJFactsEditor({ facts, documents, onChange }: MSJFactsEditorProps) {
  const [localFacts, setLocalFacts] = useState<MSJFact[]>(
    facts.length > 0 ? facts : [{ fact_number: 1, text: '', source_doc_id: null, source_excerpt: null }]
  )
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null)

  const debouncedSave = useCallback(
    (updated: MSJFact[]) => {
      if (saveTimeout) clearTimeout(saveTimeout)
      const timeout = setTimeout(() => {
        // Only save facts that have text
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

  const addFact = () => {
    const newFact: MSJFact = {
      fact_number: localFacts.length + 1,
      text: '',
      source_doc_id: null,
      source_excerpt: null,
    }
    const updated = [...localFacts, newFact]
    setLocalFacts(updated)
  }

  const removeFact = (index: number) => {
    if (localFacts.length <= 1) return
    const updated = localFacts
      .filter((_, i) => i !== index)
      .map((f, i) => ({ ...f, fact_number: i + 1 }))
    setLocalFacts(updated)
    debouncedSave(updated)
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
            List each fact with a reference to the supporting document
          </p>
        </div>
      </div>

      <div className="space-y-3">
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

              <div className="flex gap-2">
                <select
                  value={fact.source_doc_id || ''}
                  onChange={(e) =>
                    updateFact(index, {
                      source_doc_id: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                  className="px-2 py-1 border border-stone-200 rounded text-xs text-stone-600
                             focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"
                >
                  <option value="">Source document...</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      Doc #{doc.id}: {doc.title}
                    </option>
                  ))}
                </select>

                {fact.source_doc_id && (
                  <input
                    type="text"
                    value={fact.source_excerpt || ''}
                    onChange={(e) => updateFact(index, { source_excerpt: e.target.value })}
                    placeholder="Page/paragraph reference..."
                    className="flex-1 px-2 py-1 border border-stone-200 rounded text-xs
                               focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"
                  />
                )}
              </div>
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
