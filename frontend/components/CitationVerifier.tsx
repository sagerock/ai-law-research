'use client'

import { useState } from 'react'
import { Search, CheckCircle, XCircle, AlertCircle, Loader2, ExternalLink, ArrowRight, BookOpen, ShieldCheck, Copy, Check } from 'lucide-react'
import { API_URL } from '@/lib/api'

interface VerificationResult {
  found: boolean
  source: 'local_db' | 'courtlistener' | 'not_found'
  parsed: {
    case_name: string | null
    volume: number | null
    reporter: string | null
    page: number | null
    year: number | null
  }
  case: {
    id: string | null
    title: string
    reporter_cite: string | null
    neutral_cite?: string | null
    decision_date: string | null
    court: string | null
    url: string | null
  } | null
  correct_citation: string | null
  citation_mismatch: boolean
  courtlistener_url: string | null
  passage_verification: {
    found_in_opinion: boolean
    match_quality: 'exact' | 'close' | 'not_found' | 'unavailable'
    match_score?: number
    matching_excerpt?: string
    note?: string
  } | null
  error?: string
}

export default function CitationVerifier() {
  const [citationText, setCitationText] = useState('')
  const [passage, setPassage] = useState('')
  const [showPassage, setShowPassage] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [copied, setCopied] = useState(false)
  const [result, setResult] = useState<VerificationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleVerify = async () => {
    if (!citationText.trim()) return

    setIsVerifying(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/api/v1/verify-citation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          citation_text: citationText.trim(),
          passage: showPassage && passage.trim() ? passage.trim() : null,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || 'Verification failed')
      }

      const data = await response.json()
      if (data.error) {
        setError(data.error)
      }
      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Failed to verify citation. Please try again.')
      console.error(err)
    } finally {
      setIsVerifying(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleVerify()
    }
  }

  const reset = () => {
    setCitationText('')
    setPassage('')
    setResult(null)
    setError(null)
    setCopied(false)
  }

  const copyCitation = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-sage-50 text-sage-700 border border-sage-100 rounded-full px-4 py-1.5 text-sm font-medium mb-4">
          <ShieldCheck className="h-4 w-4" />
          Citation Verification Tool
        </div>
        <h1 className="font-display text-3xl sm:text-4xl text-stone-900 mb-3">
          Verify a Legal Citation
        </h1>
        <p className="text-stone-500 text-lg max-w-xl mx-auto">
          Check whether a case citation is real. Paste a citation below and we'll search our database
          and CourtListener to confirm it exists.
        </p>
      </div>

      {/* Input Card */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 mb-6 shadow-sm">
        <label htmlFor="citation-input" className="block text-sm font-medium text-stone-700 mb-2">
          Citation
        </label>
        <input
          id="citation-input"
          type="text"
          value={citationText}
          onChange={(e) => setCitationText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='e.g., "Terry v. Ohio, 392 U.S. 1 (1968)"'
          className="w-full px-4 py-3 border border-stone-200 rounded-lg text-stone-900
                     placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-sage-500
                     focus:border-transparent font-mono text-sm"
          disabled={isVerifying}
        />

        {/* Passage verification toggle */}
        <div className="mt-4">
          <button
            onClick={() => setShowPassage(!showPassage)}
            className="text-sm text-sage-600 hover:text-sage-700 flex items-center gap-1.5 transition-colors"
          >
            <BookOpen className="h-3.5 w-3.5" />
            {showPassage ? 'Hide passage verification' : 'Also verify a quoted passage (optional)'}
          </button>

          {showPassage && (
            <div className="mt-3">
              <label htmlFor="passage-input" className="block text-sm font-medium text-stone-700 mb-2">
                Quoted Passage
              </label>
              <textarea
                id="passage-input"
                value={passage}
                onChange={(e) => setPassage(e.target.value)}
                placeholder="Paste a passage attributed to this case to check if it appears in the opinion..."
                rows={3}
                className="w-full px-4 py-3 border border-stone-200 rounded-lg text-stone-900
                           placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-sage-500
                           focus:border-transparent text-sm resize-y"
                disabled={isVerifying}
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-5">
          <button
            onClick={handleVerify}
            disabled={!citationText.trim() || isVerifying}
            className="bg-sage-700 text-white py-2.5 px-6 rounded-lg hover:bg-sage-600
                       disabled:opacity-50 disabled:cursor-not-allowed transition-colors
                       flex items-center gap-2 text-sm font-medium"
          >
            {isVerifying ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Verifying...
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                Verify Citation
              </>
            )}
          </button>
          {result && (
            <button
              onClick={reset}
              className="text-sm text-stone-500 hover:text-stone-700 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-red-800 font-medium text-sm">Verification Error</p>
            <p className="text-red-700 text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="animate-fade-in">
          {/* Main result card */}
          {result.found ? (
            <div className="bg-green-50 border border-green-200 rounded-xl p-6 mb-6">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-6 w-6 text-green-600 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <h2 className="text-green-800 font-semibold text-lg">Citation Verified</h2>
                  <p className="text-green-700 text-sm mt-1">
                    This case was found {result.source === 'local_db' ? 'in our database' : 'on CourtListener'}.
                  </p>

                  {/* Citation mismatch warning */}
                  {result.citation_mismatch && (
                    <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <p className="text-yellow-800 text-sm">
                        <AlertCircle className="h-4 w-4 inline mr-1" />
                        <strong>Note:</strong> The citation you provided doesn&apos;t match this case&apos;s actual citation.
                        Use the correct citation below.
                      </p>
                    </div>
                  )}

                  {/* Correct citation with copy button */}
                  {result.correct_citation && (
                    <div className="mt-4 bg-white rounded-lg border border-green-200 p-4">
                      <p className="text-xs font-medium text-stone-500 uppercase tracking-wide mb-2">Correct Citation</p>
                      <div className="flex items-start gap-3">
                        <p className="text-stone-900 font-mono text-sm flex-1 leading-relaxed">
                          {result.correct_citation}
                        </p>
                        <button
                          onClick={() => copyCitation(result.correct_citation!)}
                          className="shrink-0 p-2 rounded-lg hover:bg-stone-100 text-stone-500 hover:text-stone-700 transition-colors"
                          title="Copy citation"
                        >
                          {copied ? (
                            <Check className="h-4 w-4 text-green-600" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  )}

                  {result.case && (
                    <div className="mt-3 bg-white/70 rounded-lg p-4 space-y-2">
                      <p className="font-semibold text-stone-900 text-base">
                        {result.case.title}
                      </p>
                      {result.case.reporter_cite && (
                        <p className="text-stone-600 text-sm font-mono">{result.case.reporter_cite}</p>
                      )}
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-stone-500">
                        {result.case.court && <span>{result.case.court}</span>}
                        {result.case.decision_date && <span>{result.case.decision_date}</span>}
                      </div>

                      {/* Links */}
                      <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-green-100">
                        {result.case.url && (
                          <a
                            href={result.case.url}
                            className="inline-flex items-center gap-1.5 text-sm text-sage-700 hover:text-sage-600 font-medium"
                          >
                            <ArrowRight className="h-3.5 w-3.5" />
                            View on Law Study Group
                          </a>
                        )}
                        {result.courtlistener_url && (
                          <a
                            href={result.courtlistener_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 text-sm text-sage-700 hover:text-sage-600 font-medium"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            View on CourtListener
                          </a>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
              <div className="flex items-start gap-3">
                <XCircle className="h-6 w-6 text-red-500 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <h2 className="text-red-800 font-semibold text-lg">Citation Not Found</h2>
                  <p className="text-red-700 text-sm mt-1">
                    This citation could not be verified in our database or on CourtListener.
                    This does not guarantee the case is fake, but it could not be confirmed.
                  </p>

                  {/* Show what was parsed */}
                  {(result.parsed.case_name || result.parsed.reporter) && (
                    <div className="mt-4 bg-white/70 rounded-lg p-4">
                      <p className="text-sm font-medium text-stone-700 mb-2">What we searched for:</p>
                      <ul className="text-sm text-stone-600 space-y-1">
                        {result.parsed.case_name && <li>Case name: {result.parsed.case_name}</li>}
                        {result.parsed.volume && result.parsed.reporter && result.parsed.page && (
                          <li>Citation: {result.parsed.volume} {result.parsed.reporter} {result.parsed.page}</li>
                        )}
                        {result.parsed.year && <li>Year: {result.parsed.year}</li>}
                      </ul>
                    </div>
                  )}

                  <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-yellow-800 text-sm">
                      <strong>Tip:</strong> If an AI tool provided this citation, it may be hallucinated.
                      Try searching for the case name directly on{' '}
                      <a
                        href="https://www.courtlistener.com/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-yellow-900"
                      >
                        CourtListener
                      </a>{' '}
                      or{' '}
                      <a
                        href="https://scholar.google.com/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline hover:text-yellow-900"
                      >
                        Google Scholar
                      </a>{' '}
                      to double-check.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Passage verification result */}
          {result.passage_verification && (
            <div className={`rounded-xl border p-6 mb-6 ${
              result.passage_verification.found_in_opinion
                ? 'bg-green-50 border-green-200'
                : result.passage_verification.match_quality === 'unavailable'
                  ? 'bg-stone-50 border-stone-200'
                  : 'bg-yellow-50 border-yellow-200'
            }`}>
              <h3 className="font-semibold text-stone-900 mb-2 flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Passage Verification
              </h3>

              {result.passage_verification.match_quality === 'exact' && (
                <div>
                  <p className="text-green-700 text-sm mb-3">
                    <CheckCircle className="h-4 w-4 inline mr-1" />
                    Exact match found in the opinion text.
                  </p>
                  {result.passage_verification.matching_excerpt && (
                    <blockquote className="bg-white/70 rounded-lg p-4 text-sm text-stone-700 border-l-4 border-green-400 italic">
                      {result.passage_verification.matching_excerpt}
                    </blockquote>
                  )}
                </div>
              )}

              {result.passage_verification.match_quality === 'close' && (
                <div>
                  <p className="text-yellow-700 text-sm mb-3">
                    <AlertCircle className="h-4 w-4 inline mr-1" />
                    A close match was found ({Math.round((result.passage_verification.match_score || 0) * 100)}% similarity).
                    The passage may be paraphrased or slightly altered.
                  </p>
                  {result.passage_verification.matching_excerpt && (
                    <blockquote className="bg-white/70 rounded-lg p-4 text-sm text-stone-700 border-l-4 border-yellow-400 italic">
                      {result.passage_verification.matching_excerpt}
                    </blockquote>
                  )}
                </div>
              )}

              {result.passage_verification.match_quality === 'not_found' && (
                <p className="text-yellow-700 text-sm">
                  <XCircle className="h-4 w-4 inline mr-1" />
                  {result.passage_verification.note || 'The quoted passage was not found in the opinion.'}
                </p>
              )}

              {result.passage_verification.match_quality === 'unavailable' && (
                <p className="text-stone-600 text-sm">
                  {result.passage_verification.note || 'Full opinion text is not available for passage verification.'}
                </p>
              )}
            </div>
          )}

          {/* Source attribution */}
          <p className="text-xs text-stone-400 text-center">
            Searches our database of {' '}
            <a href="/" className="underline hover:text-stone-500">indexed cases</a>
            {' '} and falls back to{' '}
            <a href="https://www.courtlistener.com" target="_blank" rel="noopener noreferrer" className="underline hover:text-stone-500">
              CourtListener
            </a>
            , a free legal database maintained by Free Law Project.
          </p>
        </div>
      )}

      {/* Info section */}
      {!result && !error && (
        <div className="mt-8 grid sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-stone-200 p-5">
            <div className="w-8 h-8 bg-sage-50 rounded-lg flex items-center justify-center mb-3">
              <Search className="h-4 w-4 text-sage-600" />
            </div>
            <h3 className="font-medium text-stone-900 text-sm mb-1">Multi-Source Search</h3>
            <p className="text-stone-500 text-xs leading-relaxed">
              Checks our local database first, then falls back to CourtListener's API for broader coverage.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-stone-200 p-5">
            <div className="w-8 h-8 bg-sage-50 rounded-lg flex items-center justify-center mb-3">
              <ShieldCheck className="h-4 w-4 text-sage-600" />
            </div>
            <h3 className="font-medium text-stone-900 text-sm mb-1">Catch AI Hallucinations</h3>
            <p className="text-stone-500 text-xs leading-relaxed">
              AI tools sometimes generate realistic-looking but fake citations. Verify before you cite.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-stone-200 p-5">
            <div className="w-8 h-8 bg-sage-50 rounded-lg flex items-center justify-center mb-3">
              <BookOpen className="h-4 w-4 text-sage-600" />
            </div>
            <h3 className="font-medium text-stone-900 text-sm mb-1">Passage Check</h3>
            <p className="text-stone-500 text-xs leading-relaxed">
              Optionally verify that a quoted passage actually appears in the opinion text.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
