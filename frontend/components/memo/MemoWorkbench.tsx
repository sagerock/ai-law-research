'use client'

import { useMemo, useRef, useState } from 'react'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import {
  BookOpen, FileText, Landmark, Link2, Loader2, Save, Search, Sparkles, Trash2, Upload,
} from 'lucide-react'
import type { ToolProject, ToolDocument } from '@/types'

interface Props {
  project: ToolProject
  onProjectUpdated: () => void
}

interface CaseSearchHit {
  id: string
  title: string
  reporter_cite?: string
  decision_date?: string
}

// The generated case chart, as memo_builder's CASE_CHART_SHAPE describes it.
interface CaseChart {
  issue_frame?: string
  authorities?: {
    title?: string
    citation?: string | null
    source_doc?: string
    side?: string
    why?: string
    key_passages?: { quote?: string; use?: string }[]
    fact_comparison?: { their_fact?: string; our_fact?: string; cuts?: string }[]
    how_to_use_or_distinguish?: string
  }[]
  record_gaps?: string[]
  suggested_order?: string[]
}

function parseChart(text: string | null): CaseChart | null {
  if (!text) return null
  let candidate = text.trim()
  if (candidate.startsWith('```')) {
    candidate = candidate.split('\n').slice(1).join('\n')
    if (candidate.trimEnd().endsWith('```')) candidate = candidate.trimEnd().slice(0, -3)
  }
  try {
    const chart = JSON.parse(candidate)
    return chart && typeof chart === 'object' && 'authorities' in chart ? chart : null
  } catch { return null }
}

const SIDE_STYLES: Record<string, string> = {
  helps: 'bg-sage-100 text-sage-800',
  hurts: 'bg-red-100 text-red-700',
  mixed: 'bg-amber-100 text-amber-700',
}

export default function MemoWorkbench({ project, onProjectUpdated }: Props) {
  const { session } = useAuth()
  const token = session?.access_token

  const ci = (project.case_info || {}) as Record<string, string>
  const fd = (project.form_data || {}) as Record<string, any>

  const [scenario, setScenario] = useState({
    client_name: ci.client_name || '',
    matter: ci.matter || '',
    posture: ci.posture || 'plaintiff',
    jurisdiction: ci.jurisdiction || '',
    research_question: ci.research_question || '',
    scope_notes: ci.scope_notes || '',
  })
  const [universe, setUniverse] = useState<string>(fd.universe || 'closed')
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadDocType, setUploadDocType] = useState('transcript')
  const [caseQuery, setCaseQuery] = useState('')
  const [caseHits, setCaseHits] = useState<CaseSearchHit[]>([])
  const [searching, setSearching] = useState(false)
  const [linking, setLinking] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const caseFileInput = useRef<HTMLInputElement>(null)

  const authorities = project.documents.filter((d) => d.doc_type === 'case' || d.doc_type === 'statute')
  const record = project.documents.filter((d) => d.doc_type !== 'case' && d.doc_type !== 'statute')
  const chart = useMemo(() => parseChart(project.generated_document), [project.generated_document])
  const quoteProblems: string[] = (project.document_metadata as any)?.quote_problems || []
  const isFlagged = (quote?: string) => {
    if (!quote) return false
    const squashed = quote.replace(/\s+/g, ' ').slice(0, 60)
    return quoteProblems.some((p) => p.includes(squashed.slice(0, 40)))
  }

  const authHeaders = { Authorization: `Bearer ${token}` }

  const saveScenario = async () => {
    if (!token) return
    setSaving(true); setNotice(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/tools/memo/projects/${project.id}`, {
        method: 'PUT',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: scenario.client_name ? `${scenario.client_name} memo` : undefined,
          case_info: scenario,
          form_data: { ...fd, universe },
        }),
      })
      if (res.ok) { setNotice('Scenario saved.'); onProjectUpdated() }
      else setNotice('Save failed.')
    } catch { setNotice('Save failed.') }
    finally { setSaving(false) }
  }

  const uploadFile = async (file: File, typeOverride?: string) => {
    if (!token) return
    const docType = typeOverride || uploadDocType
    setUploading(true); setNotice(null)
    try {
      const body = new FormData()
      body.append('file', file)
      body.append('doc_type', docType)
      body.append('category', docType === 'case' || docType === 'statute' ? 'authority' : 'record')
      const res = await fetch(`${API_URL}/api/v1/tools/memo/projects/${project.id}/documents`, {
        method: 'POST', headers: authHeaders, body,
      })
      if (res.ok) onProjectUpdated()
      else setNotice((await res.json().catch(() => null))?.detail || 'Upload failed.')
    } catch { setNotice('Upload failed.') }
    finally { setUploading(false); if (fileInput.current) fileInput.current.value = '' }
  }

  const deleteDoc = async (doc: ToolDocument) => {
    if (!token || !confirm(`Remove "${doc.title}" from this project?`)) return
    await fetch(`${API_URL}/api/v1/tools/memo/projects/${project.id}/documents/${doc.id}`, {
      method: 'DELETE', headers: authHeaders,
    })
    onProjectUpdated()
  }

  const searchCases = async () => {
    if (!caseQuery.trim()) return
    setSearching(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: caseQuery, limit: 6 }),
      })
      if (res.ok) {
        const data = await res.json()
        setCaseHits((data.results || []).map((r: any) => ({
          id: String(r.id), title: r.title, reporter_cite: r.reporter_cite, decision_date: r.decision_date,
        })))
      }
    } finally { setSearching(false) }
  }

  const linkCase = async (hit: CaseSearchHit) => {
    if (!token) return
    setLinking(hit.id); setNotice(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/tools/memo/projects/${project.id}/link-case`, {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: hit.id }),
      })
      if (res.ok) { setCaseHits([]); setCaseQuery(''); onProjectUpdated() }
      else setNotice((await res.json().catch(() => null))?.detail || 'Could not link case.')
    } catch { setNotice('Could not link case.') }
    finally { setLinking(null) }
  }

  const generateChart = async () => {
    if (!token) return
    if (authorities.length === 0) { setNotice('Add at least one authority first.'); return }
    setGenerating(true); setNotice(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/tools/memo/projects/${project.id}/generate`, {
        method: 'POST', headers: authHeaders,
      })
      if (!res.ok || !res.body) { setNotice('Generation failed.'); return }
      const reader = res.body.getReader()
      // Drain the SSE stream; the chart is persisted server-side when it completes.
      while (true) { const { done } = await reader.read(); if (done) break }
      onProjectUpdated()
    } catch { setNotice('Generation failed.') }
    finally { setGenerating(false) }
  }

  return (
    <main className="container mx-auto px-4 py-8 max-w-5xl">
      <h1 className="text-2xl font-display text-stone-900 mb-1">
        {scenario.client_name ? `${scenario.client_name} — memo workbench` : project.title}
      </h1>
      <p className="text-sm text-stone-500 mb-6">Scenario → record → authorities → case chart. The memo itself stays yours.</p>

      {notice && <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 text-sm text-amber-800">{notice}</div>}

      {/* Scenario */}
      <section className="bg-white rounded-xl border border-stone-200 p-5 mb-6">
        <h2 className="flex items-center gap-2 font-medium text-stone-900 mb-4"><BookOpen className="h-4 w-4 text-sage-600" /> The assignment</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input className="border border-stone-200 rounded-lg px-3 py-2 text-sm" placeholder="Client name"
            value={scenario.client_name} onChange={(e) => setScenario({ ...scenario, client_name: e.target.value })} />
          <input className="border border-stone-200 rounded-lg px-3 py-2 text-sm" placeholder="Matter (e.g. false imprisonment)"
            value={scenario.matter} onChange={(e) => setScenario({ ...scenario, matter: e.target.value })} />
          <select className="border border-stone-200 rounded-lg px-3 py-2 text-sm bg-white"
            value={scenario.posture} onChange={(e) => setScenario({ ...scenario, posture: e.target.value })}>
            <option value="plaintiff">Our client is the plaintiff</option>
            <option value="defendant">Our client is the defendant</option>
          </select>
          <input className="border border-stone-200 rounded-lg px-3 py-2 text-sm" placeholder="Jurisdiction (e.g. Ohio)"
            value={scenario.jurisdiction} onChange={(e) => setScenario({ ...scenario, jurisdiction: e.target.value })} />
        </div>
        <textarea className="mt-3 w-full border border-stone-200 rounded-lg px-3 py-2 text-sm" rows={2}
          placeholder="Research question, as the assigning attorney phrased it"
          value={scenario.research_question} onChange={(e) => setScenario({ ...scenario, research_question: e.target.value })} />
        <textarea className="mt-3 w-full border border-stone-200 rounded-lg px-3 py-2 text-sm" rows={2}
          placeholder="Scope limits (e.g. reasonableness only; no statutes beyond R.C. 2935.041)"
          value={scenario.scope_notes} onChange={(e) => setScenario({ ...scenario, scope_notes: e.target.value })} />
        <div className="mt-3 flex items-center justify-between flex-wrap gap-3">
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input type="checkbox" checked={universe === 'closed'} onChange={(e) => setUniverse(e.target.checked ? 'closed' : 'open')} />
            Closed universe (only this project&apos;s authorities may be used)
          </label>
          <button onClick={saveScenario} disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 text-sm disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save scenario
          </button>
        </div>
      </section>

      {/* Record + Authorities */}
      <div className="grid gap-6 lg:grid-cols-2 mb-6">
        <section className="bg-white rounded-xl border border-stone-200 p-5">
          <h2 className="flex items-center gap-2 font-medium text-stone-900 mb-3"><FileText className="h-4 w-4 text-sage-600" /> The record</h2>
          {record.length === 0 && <p className="text-sm text-stone-400 mb-3">Transcripts, depositions, the assigning memo.</p>}
          <ul className="space-y-2 mb-4">
            {record.map((d) => (
              <li key={d.id} className="flex items-center justify-between text-sm border border-stone-100 rounded-lg px-3 py-2 group">
                <span className="truncate"><span className="text-stone-400 text-xs mr-2">{d.doc_type}</span>{d.title}</span>
                <button onClick={() => deleteDoc(d)} className="text-stone-300 hover:text-red-500 opacity-0 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-2">
            <select className="border border-stone-200 rounded-lg px-2 py-2 text-sm bg-white" value={uploadDocType}
              onChange={(e) => setUploadDocType(e.target.value)}>
              <option value="transcript">Transcript</option>
              <option value="assignment">Assigning memo</option>
              <option value="evidence">Other record</option>
              <option value="case">Case printout</option>
              <option value="statute">Statute</option>
            </select>
            <button onClick={() => fileInput.current?.click()} disabled={uploading}
              className="flex items-center gap-2 px-3 py-2 border border-stone-300 rounded-lg text-sm text-stone-700 hover:bg-stone-50 disabled:opacity-50">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} Upload PDF / DOCX / TXT
            </button>
            <input ref={fileInput} type="file" accept=".pdf,.docx,.txt" className="hidden"
              onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0])} />
          </div>
        </section>

        <section className="bg-white rounded-xl border border-stone-200 p-5">
          <h2 className="flex items-center gap-2 font-medium text-stone-900 mb-3"><Landmark className="h-4 w-4 text-sage-600" /> The authorities</h2>
          {authorities.length === 0 && <p className="text-sm text-stone-400 mb-3">Upload case printouts (left, as &quot;Case printout&quot;) or pull cases from Tortwell below.</p>}
          <ul className="space-y-2 mb-4">
            {authorities.map((d) => (
              <li key={d.id} className="flex items-center justify-between text-sm border border-stone-100 rounded-lg px-3 py-2 group">
                <span className="truncate">
                  {d.file_type === 'tortwell' && <Link2 className="inline h-3 w-3 text-sage-500 mr-1" />}
                  {d.title}
                </span>
                <button onClick={() => deleteDoc(d)} className="text-stone-300 hover:text-red-500 opacity-0 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-2 mb-2">
            <button onClick={() => caseFileInput.current?.click()} disabled={uploading}
              className="flex items-center gap-2 px-3 py-2 border border-stone-300 rounded-lg text-sm text-stone-700 hover:bg-stone-50 disabled:opacity-50">
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />} Upload a case (PDF)
            </button>
            <input ref={caseFileInput} type="file" accept=".pdf,.docx,.txt" className="hidden"
              onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0], 'case')} />
            <span className="text-xs text-stone-400">for cases not in Tortwell</span>
          </div>
          <div className="flex items-center gap-2">
            <input className="flex-1 border border-stone-200 rounded-lg px-3 py-2 text-sm" placeholder="Search Tortwell cases…"
              value={caseQuery} onChange={(e) => setCaseQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && searchCases()} />
            <button onClick={searchCases} disabled={searching}
              className="p-2 border border-stone-300 rounded-lg text-stone-600 hover:bg-stone-50 disabled:opacity-50">
              {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            </button>
          </div>
          {caseHits.length > 0 && (
            <ul className="mt-2 border border-stone-200 rounded-lg divide-y divide-stone-100">
              {caseHits.map((hit) => (
                <li key={hit.id} className="flex items-center justify-between px-3 py-2 text-sm">
                  <span className="truncate">{hit.title} {hit.reporter_cite && <span className="text-stone-400 text-xs">{hit.reporter_cite}</span>}</span>
                  <button onClick={() => linkCase(hit)} disabled={linking === hit.id}
                    className="text-sage-700 hover:text-sage-600 text-xs font-medium disabled:opacity-50">
                    {linking === hit.id ? 'Linking…' : 'Link'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Case chart */}
      <section className="bg-white rounded-xl border border-stone-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="flex items-center gap-2 font-medium text-stone-900"><Sparkles className="h-4 w-4 text-sage-600" /> Case chart</h2>
          <button onClick={generateChart} disabled={generating || authorities.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 text-sm disabled:opacity-50">
            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {chart ? 'Regenerate chart' : 'Generate chart'}
          </button>
        </div>

        {generating && <p className="text-sm text-stone-500">Analyzing {authorities.length} authorities against the record…</p>}

        {!generating && !chart && (
          <p className="text-sm text-stone-400">
            The chart maps every authority to your facts: helps, hurts, or mixed — with the verbatim
            passages that matter and how to use or distinguish each case. AI-generated; verify every
            quote against the source before it goes anywhere near your memo.
          </p>
        )}

        {!generating && chart && (
          <div className="space-y-4">
            {quoteProblems.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-sm text-amber-800">
                {quoteProblems.length} quote{quoteProblems.length > 1 ? 's' : ''} did not match the source verbatim —
                marked below. Check each against the document before relying on it (the model may have
                silently corrected a typo, or paraphrased).
              </div>
            )}
            {chart.issue_frame && <p className="text-sm text-stone-700 font-medium">{chart.issue_frame}</p>}
            {(chart.authorities || []).map((a, i) => (
              <div key={i} className="border border-stone-200 rounded-lg p-4">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-medium text-stone-900">{a.title}</span>
                  {a.citation && <span className="text-xs text-stone-400 font-mono">{a.citation}</span>}
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SIDE_STYLES[a.side || ''] || 'bg-stone-100 text-stone-600'}`}>{a.side}</span>
                </div>
                {a.why && <p className="text-sm text-stone-600 mb-2">{a.why}</p>}
                {(a.key_passages || []).map((p, j) => {
                  const flagged = isFlagged(p.quote)
                  return (
                    <blockquote key={j} className={`border-l-2 pl-3 my-2 text-sm italic ${flagged ? 'border-amber-400 bg-amber-50 text-stone-800 py-1.5 pr-2 rounded-r' : 'border-sage-200 text-stone-700'}`}>
                      &ldquo;{p.quote}&rdquo;
                      {flagged && <span className="block not-italic text-xs font-medium text-amber-700 mt-1">⚠ Not verbatim in the source — verify before using</span>}
                      {p.use && <span className="block not-italic text-xs text-stone-500 mt-1">{p.use}</span>}
                    </blockquote>
                  )
                })}
                {a.how_to_use_or_distinguish && (
                  <p className="text-sm text-stone-700 mt-2"><span className="font-medium">The move:</span> {a.how_to_use_or_distinguish}</p>
                )}
              </div>
            ))}
            {(chart.record_gaps || []).length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <p className="text-sm font-medium text-amber-800 mb-1">The record doesn&apos;t establish:</p>
                <ul className="list-disc pl-5 text-sm text-amber-700">
                  {chart.record_gaps!.map((g, i) => <li key={i}>{g}</li>)}
                </ul>
              </div>
            )}
            {(chart.suggested_order || []).length > 0 && (
              <div>
                <p className="text-sm font-medium text-stone-900 mb-1">Suggested discussion order</p>
                <ol className="list-decimal pl-5 text-sm text-stone-600">
                  {chart.suggested_order!.map((s, i) => <li key={i}>{s}</li>)}
                </ol>
              </div>
            )}
            <p className="text-xs text-stone-400">AI-generated chart. Verify every quote and every characterization against the source documents.</p>
          </div>
        )}
      </section>
    </main>
  )
}
