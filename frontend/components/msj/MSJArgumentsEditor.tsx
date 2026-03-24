'use client'

import { useState, useCallback, useEffect } from 'react'
import { Plus, Trash2, MessageSquare, ChevronDown, ChevronUp } from 'lucide-react'
import type { MSJArgument } from '@/types'

interface MSJArgumentsEditorProps {
  arguments: MSJArgument[]
  onChange: (args: MSJArgument[]) => void
}

export default function MSJArgumentsEditor({ arguments: args, onChange }: MSJArgumentsEditorProps) {
  const [localArgs, setLocalArgs] = useState<MSJArgument[]>(
    args.length > 0
      ? args
      : [{ issue: '', standard: '', argument_text: '', supporting_case_ids: [], supporting_rule_ids: [] }]
  )
  const [expandedIndex, setExpandedIndex] = useState<number>(0)
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null)

  const debouncedSave = useCallback(
    (updated: MSJArgument[]) => {
      if (saveTimeout) clearTimeout(saveTimeout)
      const timeout = setTimeout(() => {
        const nonEmpty = updated.filter((a) => a.issue.trim())
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

  const updateArg = (index: number, updates: Partial<MSJArgument>) => {
    const updated = localArgs.map((a, i) => (i === index ? { ...a, ...updates } : a))
    setLocalArgs(updated)
    debouncedSave(updated)
  }

  const addArgument = () => {
    const newArg: MSJArgument = {
      issue: '',
      standard: '',
      argument_text: '',
      supporting_case_ids: [],
      supporting_rule_ids: [],
    }
    const updated = [...localArgs, newArg]
    setLocalArgs(updated)
    setExpandedIndex(updated.length - 1)
  }

  const removeArgument = (index: number) => {
    if (localArgs.length <= 1) return
    const updated = localArgs.filter((_, i) => i !== index)
    setLocalArgs(updated)
    setExpandedIndex(Math.min(expandedIndex, updated.length - 1))
    debouncedSave(updated)
  }

  const romanNumeral = (n: number): string => {
    const numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
    return numerals[n] || String(n + 1)
  }

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
          <MessageSquare className="h-5 w-5 text-sage-700" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-stone-900">Legal Arguments</h2>
          <p className="text-sm text-stone-500">
            Define the legal issues and arguments for summary judgment
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {localArgs.map((arg, index) => {
          const isExpanded = expandedIndex === index
          return (
            <div key={index} className="border border-stone-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedIndex(isExpanded ? -1 : index)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-stone-50 transition-colors text-left"
              >
                <span className="text-sm font-medium text-sage-700 w-8">
                  {romanNumeral(index)}.
                </span>
                <span className="flex-1 text-sm text-stone-700 truncate">
                  {arg.issue || 'New argument...'}
                </span>
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4 text-stone-400" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-stone-400" />
                )}
              </button>

              {isExpanded && (
                <div className="px-4 pb-4 space-y-3 border-t border-stone-100">
                  <div className="pt-3">
                    <label className="block text-sm font-medium text-stone-700 mb-1">
                      Legal Issue
                    </label>
                    <input
                      type="text"
                      value={arg.issue}
                      onChange={(e) => updateArg(index, { issue: e.target.value })}
                      placeholder="e.g., No genuine dispute of material fact exists regarding breach of contract"
                      className="w-full px-3 py-2 border border-stone-200 rounded-lg text-sm
                                 focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-1">
                      Legal Standard
                    </label>
                    <textarea
                      value={arg.standard}
                      onChange={(e) => updateArg(index, { standard: e.target.value })}
                      placeholder="e.g., Under Rule 56, summary judgment is appropriate when there is no genuine dispute as to any material fact..."
                      rows={2}
                      className="w-full px-3 py-2 border border-stone-200 rounded-lg text-sm
                                 focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent
                                 resize-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-1">
                      Argument
                    </label>
                    <textarea
                      value={arg.argument_text}
                      onChange={(e) => updateArg(index, { argument_text: e.target.value })}
                      placeholder="Explain how the undisputed facts satisfy the legal standard..."
                      rows={4}
                      className="w-full px-3 py-2 border border-stone-200 rounded-lg text-sm
                                 focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent
                                 resize-none"
                    />
                  </div>

                  <div className="flex justify-end">
                    <button
                      onClick={() => removeArgument(index)}
                      disabled={localArgs.length <= 1}
                      className="flex items-center gap-1.5 text-xs text-stone-400 hover:text-red-500
                                 disabled:opacity-30 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button
        onClick={addArgument}
        className="flex items-center gap-2 mt-4 px-3 py-2 text-sm text-sage-700 hover:bg-sage-50
                   rounded-lg transition-colors"
      >
        <Plus className="h-4 w-4" /> Add Argument
      </button>
    </div>
  )
}
