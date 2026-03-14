'use client'

import { useState } from 'react'
import { X, Sparkles, Loader2 } from 'lucide-react'

const LAW_SUBJECTS = [
  'Civil Procedure', 'Constitutional Law', 'Contracts', 'Criminal Law',
  'Criminal Procedure', 'Evidence', 'Property', 'Torts',
  'Administrative Law', 'Business Associations', 'Family Law',
  'Professional Responsibility', 'Remedies', 'Secured Transactions',
  'Trusts & Estates', 'Other',
]

interface GenerateMindmapModalProps {
  apiUrl: string
  getAuthHeaders: () => Record<string, string>
  onGenerated: (tree: any) => void
  onClose: () => void
}

export default function GenerateMindmapModal({
  apiUrl, getAuthHeaders, onGenerated, onClose
}: GenerateMindmapModalProps) {
  const [topic, setTopic] = useState('')
  const [subject, setSubject] = useState('')
  const [depth, setDepth] = useState(3)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleGenerate = async () => {
    if (!topic.trim()) return
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${apiUrl}/api/v1/study/mindmaps/generate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          topic: topic.trim(),
          subject: subject || undefined,
          depth,
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Generation failed' }))
        throw new Error(body.detail || 'Failed to generate mindmap')
      }

      const data = await res.json()
      onGenerated(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-stone-800 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-sage-600" />
            Generate Mindmap with AI
          </h3>
          <button onClick={onClose} className="text-stone-400 hover:text-stone-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Topic */}
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Topic</label>
            <input
              type="text"
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="e.g., Rule 12 Motions, Criminal Homicide, Due Process..."
              className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-sage-500"
              onKeyDown={e => { if (e.key === 'Enter' && !loading) handleGenerate() }}
              autoFocus
            />
          </div>

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Subject (optional)</label>
            <select
              value={subject}
              onChange={e => setSubject(e.target.value)}
              className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-sage-500 bg-white"
            >
              <option value="">Select subject...</option>
              {LAW_SUBJECTS.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Depth */}
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Depth: {depth} levels
            </label>
            <input
              type="range"
              min={2}
              max={4}
              value={depth}
              onChange={e => setDepth(parseInt(e.target.value))}
              className="w-full accent-sage-600"
            />
            <div className="flex justify-between text-xs text-stone-400">
              <span>Overview</span>
              <span>Detailed</span>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
              <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
            </div>
          )}

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={loading || !topic.trim()}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-sage-600 text-white rounded-lg font-medium hover:bg-sage-700 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate
              </>
            )}
          </button>

          <p className="text-xs text-stone-400 text-center">
            AI will generate a study mindmap tree you can edit before saving
          </p>
        </div>
      </div>
    </div>
  )
}
