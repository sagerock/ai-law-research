'use client'

import { useState, useEffect, useCallback } from 'react'
import { User } from 'lucide-react'
import type { AffiantInfo as AffiantInfoType } from '@/types'

interface AffiantInfoProps {
  affiantInfo: AffiantInfoType
  onChange: (info: AffiantInfoType) => void
}

export default function AffiantInfo({ affiantInfo, onChange }: AffiantInfoProps) {
  const [form, setForm] = useState<AffiantInfoType>(affiantInfo)
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null)

  const debouncedSave = useCallback(
    (updated: AffiantInfoType) => {
      if (saveTimeout) clearTimeout(saveTimeout)
      const timeout = setTimeout(() => onChange(updated), 800)
      setSaveTimeout(timeout)
    },
    [onChange, saveTimeout]
  )

  const updateField = (field: keyof AffiantInfoType, value: string | boolean) => {
    const updated = { ...form, [field]: value }
    setForm(updated)
    debouncedSave(updated)
  }

  useEffect(() => {
    return () => { if (saveTimeout) clearTimeout(saveTimeout) }
  }, [saveTimeout])

  const inputClass = "w-full px-3 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
          <User className="h-5 w-5 text-sage-700" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-stone-900">Affiant Information</h2>
          <p className="text-sm text-stone-500">Who is making this affidavit and how do they know the facts?</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Full Name</label>
            <input
              type="text"
              value={form.name || ''}
              onChange={(e) => updateField('name', e.target.value)}
              placeholder="e.g., Patrick Downing"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Title / Role</label>
            <input
              type="text"
              value={form.title || ''}
              onChange={(e) => updateField('title', e.target.value)}
              placeholder="e.g., Eyewitness, Supervisor, Expert"
              className={inputClass}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Relationship to Case</label>
          <textarea
            value={form.relationship_to_case || ''}
            onChange={(e) => updateField('relationship_to_case', e.target.value)}
            placeholder="Describe how this person is connected to the case. e.g., 'Eyewitness to the accident at the intersection of Main and Oak on March 5, 2024'"
            rows={2}
            className={inputClass + ' resize-none'}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Employer (if relevant)</label>
          <input
            type="text"
            value={form.employer || ''}
            onChange={(e) => updateField('employer', e.target.value)}
            placeholder="e.g., ZAMR Corp."
            className={inputClass}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Basis of Personal Knowledge</label>
          <textarea
            value={form.knowledge_basis || ''}
            onChange={(e) => updateField('knowledge_basis', e.target.value)}
            placeholder="How does this person have firsthand knowledge? e.g., 'Was present at the scene and personally observed the events described below'"
            rows={3}
            className={inputClass + ' resize-none'}
          />
        </div>

        <div className="flex items-start gap-3 p-4 bg-sage-50 rounded-lg border border-sage-200">
          <input
            type="checkbox"
            id="personal-knowledge"
            checked={form.has_personal_knowledge || false}
            onChange={(e) => updateField('has_personal_knowledge', e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-stone-300 text-sage-600 focus:ring-sage-500"
          />
          <label htmlFor="personal-knowledge" className="text-sm text-stone-700">
            <span className="font-medium">Affiant has personal knowledge</span>
            <span className="block text-xs text-stone-500 mt-0.5">
              Under FRCP 56(c)(4), every statement must be based on the affiant&apos;s personal knowledge.
              Check this to confirm the affiant personally observed or participated in the events described.
            </span>
          </label>
        </div>
      </div>
    </div>
  )
}
