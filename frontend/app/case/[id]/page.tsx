'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Calendar, FileText, TrendingUp, Scale, ExternalLink, Copy, CheckCircle, Sparkles, AlertCircle, BookOpen, Gavel, Loader2 } from 'lucide-react'
import { API_URL } from '@/lib/api'

interface CaseDetail {
  id: string
  title?: string
  case_name?: string
  court_id: string
  court_name?: string
  decision_date?: string
  date_filed?: string
  citation_count?: number
  url?: string
  source_url?: string
  content?: string
  metadata?: any
}

interface CaseSummary {
  summary: string
  cost: number
  citing_cases: Array<{
    id: string
    case_name: string
    date_filed: string
    court_id: string
  }>
  cited_cases: Array<{
    id: string
    case_name: string
    date_filed: string
    court_id: string
  }>
}

export default function CaseDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [caseData, setCaseData] = useState<CaseDetail | null>(null)
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [copiedCitation, setCopiedCitation] = useState(false)

  useEffect(() => {
    fetchCase()
  }, [params.id])

  const fetchCase = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/cases/${params.id}`)
      if (!response.ok) throw new Error('Case not found')
      const data = await response.json()
      setCaseData(data)
    } catch (err) {
      setError('Failed to load case')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const generateSummary = async () => {
    setSummaryLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/cases/${params.id}/summarize`, {
        method: 'POST'
      })
      if (!response.ok) throw new Error('Failed to generate summary')
      const data = await response.json()
      setCaseSummary(data)
    } catch (err) {
      console.error('Failed to generate summary:', err)
    } finally {
      setSummaryLoading(false)
    }
  }

  const handleCopy = () => {
    if (caseData?.content) {
      navigator.clipboard.writeText(caseData.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleCopyCitation = () => {
    if (caseData) {
      const caseName = caseData.title || caseData.case_name || 'Unknown Case'
      const dateStr = caseData.decision_date || caseData.date_filed
      const year = dateStr ? new Date(dateStr).getFullYear() : ''
      const citation = `${caseName}, ${caseData.metadata?.citation || ''} (${caseData.court_id} ${year})`
      navigator.clipboard.writeText(citation)
      setCopiedCitation(true)
      setTimeout(() => setCopiedCitation(false), 2000)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-neutral-100">
        <div className="container mx-auto px-4 py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-neutral-200 rounded w-1/3 mb-4"></div>
            <div className="h-4 bg-neutral-200 rounded w-1/4 mb-8"></div>
            <div className="space-y-3">
              <div className="h-4 bg-neutral-200 rounded"></div>
              <div className="h-4 bg-neutral-200 rounded"></div>
              <div className="h-4 bg-neutral-200 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !caseData) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-neutral-100">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center py-12">
            <p className="text-xl text-red-600 mb-4">{error || 'Case not found'}</p>
            <Link href="/" className="text-blue-600 hover:text-blue-700">
              Return to Search
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-neutral-100">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => router.back()}
              className="flex items-center text-neutral-600 hover:text-neutral-900"
            >
              <ArrowLeft className="h-5 w-5 mr-2" />
              Back to Results
            </button>
            <Link href="/" className="flex items-center">
              <Scale className="h-6 w-6 text-neutral-700 mr-2" />
              <span className="text-xl font-bold text-neutral-900">Legal Research Tool</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Case Content */}
      <main className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content - Left 2/3 */}
          <div className="lg:col-span-2 space-y-6">
            {/* Case Header */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h1 className="text-2xl font-bold text-neutral-900 mb-4">
                {caseData.title || caseData.case_name}
              </h1>

              {/* Case Metadata */}
              <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-600 mb-4">
                <span className="flex items-center">
                  <FileText className="h-4 w-4 mr-1" />
                  {caseData.court_name || caseData.court_id}
                </span>
                {(caseData.decision_date || caseData.date_filed) && (
                  <span className="flex items-center">
                    <Calendar className="h-4 w-4 mr-1" />
                    {new Date(caseData.decision_date || caseData.date_filed || '').toLocaleDateString()}
                  </span>
                )}
                {caseData.citation_count !== undefined && (
                  <span className="flex items-center">
                    <TrendingUp className="h-4 w-4 mr-1" />
                    Cited {caseData.citation_count} times
                  </span>
                )}
              </div>

              {/* Citation Info */}
              {caseData.metadata?.citation && (
                <div className="bg-blue-50 text-blue-700 px-3 py-2 rounded inline-block mb-4">
                  Citation: {caseData.metadata.citation}
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleCopy}
                  className="flex items-center px-4 py-2 bg-neutral-100 hover:bg-neutral-200 rounded-lg text-neutral-700"
                >
                  {copied ? (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4 mr-2" />
                      Copy Text
                    </>
                  )}
                </button>
                <button
                  onClick={handleCopyCitation}
                  className="flex items-center px-4 py-2 bg-neutral-100 hover:bg-neutral-200 rounded-lg text-neutral-700"
                >
                  {copiedCitation ? (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <BookOpen className="h-4 w-4 mr-2" />
                      Copy Citation
                    </>
                  )}
                </button>
                {caseData.url && (
                  <a
                    href={caseData.url.startsWith('http') ? caseData.url : `https://www.courtlistener.com${caseData.url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View on CourtListener
                  </a>
                )}
              </div>
            </div>

            {/* AI Summary */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-neutral-900 flex items-center">
                  <Sparkles className="h-5 w-5 mr-2 text-purple-600" />
                  AI Case Brief
                </h2>
                {!caseSummary && (
                  <button
                    onClick={generateSummary}
                    disabled={summaryLoading}
                    className="flex items-center px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm disabled:bg-neutral-400"
                  >
                    {summaryLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4 mr-2" />
                        Generate Summary
                      </>
                    )}
                  </button>
                )}
              </div>

              {caseSummary ? (
                <div className="space-y-4">
                  <div className="prose prose-sm max-w-none">
                    {caseSummary.summary.split('\n').map((line, idx) => {
                      if (line.includes('**')) {
                        const parts = line.split('**')
                        return (
                          <div key={idx} className="mb-3">
                            <h4 className="font-semibold text-neutral-800 mb-1">
                              {parts[1]}
                            </h4>
                            <p className="text-neutral-700">{parts[2]}</p>
                          </div>
                        )
                      }
                      return line.trim() && <p key={idx} className="text-neutral-700 mb-2">{line}</p>
                    })}
                  </div>
                  <div className="text-xs text-neutral-500 border-t pt-2">
                    Generated by GPT-5-mini • Cost: ${caseSummary.cost.toFixed(4)}
                  </div>
                </div>
              ) : (
                <p className="text-neutral-500">
                  Click "Generate Summary" to create an AI-powered case brief with facts, issues, holdings, and reasoning.
                </p>
              )}
            </div>

            {/* Case Text */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-neutral-900 mb-4">Full Opinion</h2>
              {caseData.content && caseData.content.length > 50 ? (
                <div className="prose prose-neutral max-w-none">
                  {/* Check if content contains HTML tags */}
                  {caseData.content.includes('<') && caseData.content.includes('>') ? (
                    <div
                      className="text-sm leading-relaxed text-neutral-700"
                      dangerouslySetInnerHTML={{ __html: caseData.content }}
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-neutral-700">
                      {caseData.content}
                    </pre>
                  )}
                </div>
              ) : (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
                  <AlertCircle className="h-12 w-12 text-blue-600 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                    Full Opinion Text Not Available
                  </h3>
                  <p className="text-neutral-600 mb-4">
                    The complete opinion text is not available in our database.
                    Please view the full case on CourtListener.
                  </p>
                  {(() => {
                    const courtListenerUrl = caseData.url || caseData.source_url || caseData.metadata?.absolute_url
                    if (!courtListenerUrl) return null

                    const fullUrl = courtListenerUrl.startsWith('http')
                      ? courtListenerUrl
                      : `https://www.courtlistener.com${courtListenerUrl}`

                    return (
                      <a
                        href={fullUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
                      >
                        <ExternalLink className="h-5 w-5 mr-2" />
                        View Full Opinion on CourtListener
                      </a>
                    )
                  })()}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar - Right 1/3 */}
          <div className="space-y-6">
            {/* Citations Panel */}
            {caseSummary && (
              <>
                {/* Cases Citing This Case */}
                {caseSummary.citing_cases.length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm border p-4">
                    <h3 className="text-md font-semibold text-neutral-900 mb-3 flex items-center">
                      <TrendingUp className="h-4 w-4 mr-2 text-green-600" />
                      Cited By ({caseSummary.citing_cases.length})
                    </h3>
                    <div className="space-y-2">
                      {caseSummary.citing_cases.map((c) => (
                        <Link
                          key={c.id}
                          href={`/case/${c.id}`}
                          className="block p-2 hover:bg-neutral-50 rounded border border-transparent hover:border-neutral-200"
                        >
                          <p className="text-sm font-medium text-blue-600 hover:text-blue-700 line-clamp-2">
                            {c.case_name}
                          </p>
                          <p className="text-xs text-neutral-500 mt-1">
                            {c.court_id} • {new Date(c.date_filed).getFullYear()}
                          </p>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {/* Cases This Case Cites */}
                {caseSummary.cited_cases.length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm border p-4">
                    <h3 className="text-md font-semibold text-neutral-900 mb-3 flex items-center">
                      <Gavel className="h-4 w-4 mr-2 text-blue-600" />
                      Cites ({caseSummary.cited_cases.length})
                    </h3>
                    <div className="space-y-2">
                      {caseSummary.cited_cases.map((c) => (
                        <Link
                          key={c.id}
                          href={`/case/${c.id}`}
                          className="block p-2 hover:bg-neutral-50 rounded border border-transparent hover:border-neutral-200"
                        >
                          <p className="text-sm font-medium text-blue-600 hover:text-blue-700 line-clamp-2">
                            {c.case_name}
                          </p>
                          <p className="text-xs text-neutral-500 mt-1">
                            {c.court_id} • {new Date(c.date_filed).getFullYear()}
                          </p>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Additional Metadata */}
            {caseData.metadata && Object.keys(caseData.metadata).length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border p-4">
                <h3 className="text-md font-semibold text-neutral-900 mb-3">Additional Information</h3>
                <dl className="space-y-3">
                  {Object.entries(caseData.metadata)
                    .filter(([key, value]) => {
                      // Only show useful, non-complex fields
                      if (typeof value === 'object' && value !== null) return false
                      // Skip empty or very long values
                      if (!value || (typeof value === 'string' && value.length > 200)) return false
                      // Skip technical fields
                      if (['meta', 'opinions'].includes(key)) return false
                      return true
                    })
                    .map(([key, value]) => (
                      <div key={key} className="pb-2 border-b border-neutral-100 last:border-0">
                        <dt className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">
                          {key.replace(/_/g, ' ')}
                        </dt>
                        <dd className="text-sm text-neutral-900 break-words">
                          {String(value)}
                        </dd>
                      </div>
                    ))}
                </dl>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}