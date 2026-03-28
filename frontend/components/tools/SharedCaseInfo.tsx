'use client'

import { useState, useEffect, useCallback } from 'react'
import { Scale } from 'lucide-react'
import type { MSJCaseInfo as CaseInfoType } from '@/types'

interface SharedCaseInfoProps {
  caseInfo: CaseInfoType
  onChange: (info: CaseInfoType) => void
}

export default function SharedCaseInfo({ caseInfo, onChange }: SharedCaseInfoProps) {
  const [form, setForm] = useState<CaseInfoType>(caseInfo)
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null)

  const debouncedSave = useCallback(
    (updated: CaseInfoType) => {
      if (saveTimeout) clearTimeout(saveTimeout)
      const timeout = setTimeout(() => onChange(updated), 800)
      setSaveTimeout(timeout)
    },
    [onChange, saveTimeout]
  )

  const updateField = (field: keyof CaseInfoType, value: string) => {
    const updated = { ...form, [field]: value }
    setForm(updated)
    debouncedSave(updated)
  }

  useEffect(() => {
    return () => {
      if (saveTimeout) clearTimeout(saveTimeout)
    }
  }, [saveTimeout])

  const inputClass = "w-full px-3 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
          <Scale className="h-5 w-5 text-sage-700" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-stone-900">Case Information</h2>
          <p className="text-sm text-stone-500">Enter the basic details about the case</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Plaintiff</label>
          <input type="text" value={form.plaintiff || ''} onChange={(e) => updateField('plaintiff', e.target.value)} placeholder="e.g., John Smith" className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Defendant</label>
          <input type="text" value={form.defendant || ''} onChange={(e) => updateField('defendant', e.target.value)} placeholder="e.g., ABC Corporation" className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Court</label>
          <input type="text" value={form.court || ''} onChange={(e) => updateField('court', e.target.value)} placeholder="e.g., U.S. District Court, Northern District of Ohio" className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Jurisdiction</label>
          <select value={form.jurisdiction || ''} onChange={(e) => updateField('jurisdiction', e.target.value)} className={inputClass}>
            <option value="">Select jurisdiction...</option>
            <option value="federal">Federal</option>
            <option value="alabama">Alabama</option><option value="alaska">Alaska</option><option value="arizona">Arizona</option>
            <option value="arkansas">Arkansas</option><option value="california">California</option><option value="colorado">Colorado</option>
            <option value="connecticut">Connecticut</option><option value="delaware">Delaware</option><option value="florida">Florida</option>
            <option value="georgia">Georgia</option><option value="hawaii">Hawaii</option><option value="idaho">Idaho</option>
            <option value="illinois">Illinois</option><option value="indiana">Indiana</option><option value="iowa">Iowa</option>
            <option value="kansas">Kansas</option><option value="kentucky">Kentucky</option><option value="louisiana">Louisiana</option>
            <option value="maine">Maine</option><option value="maryland">Maryland</option><option value="massachusetts">Massachusetts</option>
            <option value="michigan">Michigan</option><option value="minnesota">Minnesota</option><option value="mississippi">Mississippi</option>
            <option value="missouri">Missouri</option><option value="montana">Montana</option><option value="nebraska">Nebraska</option>
            <option value="nevada">Nevada</option><option value="new_hampshire">New Hampshire</option><option value="new_jersey">New Jersey</option>
            <option value="new_mexico">New Mexico</option><option value="new_york">New York</option><option value="north_carolina">North Carolina</option>
            <option value="north_dakota">North Dakota</option><option value="ohio">Ohio</option><option value="oklahoma">Oklahoma</option>
            <option value="oregon">Oregon</option><option value="pennsylvania">Pennsylvania</option><option value="rhode_island">Rhode Island</option>
            <option value="south_carolina">South Carolina</option><option value="south_dakota">South Dakota</option><option value="tennessee">Tennessee</option>
            <option value="texas">Texas</option><option value="utah">Utah</option><option value="vermont">Vermont</option>
            <option value="virginia">Virginia</option><option value="washington">Washington</option><option value="west_virginia">West Virginia</option>
            <option value="wisconsin">Wisconsin</option><option value="wyoming">Wyoming</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Case Number</label>
          <input type="text" value={form.case_number || ''} onChange={(e) => updateField('case_number', e.target.value)} placeholder="e.g., 1:24-cv-01234" className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Representing</label>
          <select value={form.representing_side || ''} onChange={(e) => updateField('representing_side', e.target.value)} className={inputClass}>
            <option value="">Select side...</option>
            <option value="plaintiff">Plaintiff</option>
            <option value="defendant">Defendant</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">County</label>
          <input type="text" value={form.county || ''} onChange={(e) => updateField('county', e.target.value)} placeholder="e.g., Summit" className={inputClass} />
        </div>
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Judge (optional)</label>
          <input type="text" value={form.judge || ''} onChange={(e) => updateField('judge', e.target.value)} placeholder="e.g., Hon. Jane Doe" className={inputClass} />
        </div>
      </div>
    </div>
  )
}
