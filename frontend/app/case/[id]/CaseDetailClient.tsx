'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Calendar, FileText, TrendingUp, Scale, ExternalLink, Copy, CheckCircle, Sparkles, AlertCircle, BookOpen, Gavel, Loader2, Bookmark, FolderPlus, Check, ChevronDown } from 'lucide-react'
import { API_URL } from '@/lib/api'
import { UserMenu } from '@/components/auth/UserMenu'
import { useAuth } from '@/lib/auth-context'
import Comments from '@/components/Comments'

export interface CaseDetail {
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
  content_type?: string
  pdf_url?: string
  metadata?: any
}

interface CaseSummary {
  summary: string
  cost: number
  citing_cases: Array<CaseReference>
  cited_cases: Array<CaseReference>
  tokens_used?: {
    input: number
    output: number
    total: number
  }
  model?: string
}

interface CaseReference {
  id: string
  title?: string
  case_name?: string
  decision_date?: string
  date_filed?: string
  court_name?: string
  court_id?: string
  signal?: string
  snippet?: string
}

interface CitationData {
  case_id: string
  citing_cases: Array<CaseReference>
  cited_cases: Array<CaseReference>
  citing_count: number
  cited_count: number
}

interface CaseDetailClientProps {
  caseData: CaseDetail
  caseId: string
}

interface UserCollection {
  id: string
  name: string
  subject: string | null
  case_count: number
}

export default function CaseDetailClient({ caseData, caseId }: CaseDetailClientProps) {
  const router = useRouter()
  const { user, session } = useAuth()
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null)
  const [citations, setCitations] = useState<CitationData | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [copiedCitation, setCopiedCitation] = useState(false)

  // Library feature state
  const [isBookmarked, setIsBookmarked] = useState(false)
  const [bookmarkLoading, setBookmarkLoading] = useState(false)
  const [collections, setCollections] = useState<UserCollection[]>([])
  const [showCollectionDropdown, setShowCollectionDropdown] = useState(false)
  const [addingToCollection, setAddingToCollection] = useState<string | null>(null)
  const [caseInCollections, setCaseInCollections] = useState<Set<string>>(new Set())
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Get auth headers for API calls
  const getAuthHeaders = (): Record<string, string> => {
    if (!session?.access_token) return {}
    return {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json'
    }
  }

  useEffect(() => {
    fetchCachedSummary()
    fetchCitations()
  }, [caseId])

  // Fetch library data when user is logged in
  useEffect(() => {
    if (user && session?.access_token) {
      checkBookmarkStatus()
      fetchUserCollections()
    }
  }, [user, session, caseId])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowCollectionDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Check if case is bookmarked
  const checkBookmarkStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/library/bookmarks/check/${caseId}`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setIsBookmarked(data.bookmarked)
      }
    } catch (err) {
      console.log('Failed to check bookmark status:', err)
    }
  }

  // Fetch user collections and check which contain this case
  const fetchUserCollections = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setCollections(data.collections)

        // Check which collections contain this case
        const inCollections = new Set<string>()
        for (const collection of data.collections) {
          const detailResponse = await fetch(`${API_URL}/api/v1/library/collections/${collection.id}`, {
            headers: getAuthHeaders()
          })
          if (detailResponse.ok) {
            const detail = await detailResponse.json()
            if (detail.cases.some((c: { id: string }) => c.id === caseId)) {
              inCollections.add(collection.id)
            }
          }
        }
        setCaseInCollections(inCollections)
      }
    } catch (err) {
      console.log('Failed to fetch collections:', err)
    }
  }

  // Toggle bookmark
  const toggleBookmark = async () => {
    if (!user || !session?.access_token) {
      router.push('/login')
      return
    }

    setBookmarkLoading(true)
    try {
      if (isBookmarked) {
        const response = await fetch(`${API_URL}/api/v1/library/bookmarks/${caseId}`, {
          method: 'DELETE',
          headers: getAuthHeaders()
        })
        if (response.ok) {
          setIsBookmarked(false)
        }
      } else {
        const response = await fetch(`${API_URL}/api/v1/library/bookmarks`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ case_id: caseId })
        })
        if (response.ok) {
          setIsBookmarked(true)
        }
      }
    } catch (err) {
      console.error('Failed to toggle bookmark:', err)
    } finally {
      setBookmarkLoading(false)
    }
  }

  // Add/remove case to/from collection
  const toggleCollection = async (collectionId: string) => {
    if (!user || !session?.access_token) return

    setAddingToCollection(collectionId)
    try {
      if (caseInCollections.has(collectionId)) {
        // Remove from collection
        const response = await fetch(`${API_URL}/api/v1/library/collections/${collectionId}/cases/${caseId}`, {
          method: 'DELETE',
          headers: getAuthHeaders()
        })
        if (response.ok) {
          setCaseInCollections(prev => {
            const newSet = new Set(prev)
            newSet.delete(collectionId)
            return newSet
          })
        }
      } else {
        // Add to collection
        const response = await fetch(`${API_URL}/api/v1/library/collections/${collectionId}/cases`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ case_id: caseId })
        })
        if (response.ok) {
          setCaseInCollections(prev => new Set(prev).add(collectionId))
        }
      }
    } catch (err) {
      console.error('Failed to update collection:', err)
    } finally {
      setAddingToCollection(null)
    }
  }

  const fetchCachedSummary = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/summary`)
      if (!response.ok) return
      const data = await response.json()
      if (data.cached && data.summary) {
        setCaseSummary(data)
        console.log('Loaded cached summary')
      }
    } catch (err) {
      console.log('No cached summary available')
    }
  }

  const fetchCitations = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/citations`)
      if (!response.ok) return
      const data = await response.json()
      setCitations(data)
      console.log(`Loaded ${data.citing_count} citing cases, ${data.cited_count} cited cases`)
    } catch (err) {
      console.log('Failed to load citations:', err)
    }
  }

  const generateSummary = async () => {
    setSummaryLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/summarize`, {
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
            <div className="flex items-center gap-6">
              <Link href="/" className="flex items-center">
                <Scale className="h-6 w-6 text-neutral-700 mr-2" />
                <span className="text-xl font-bold text-neutral-900">Sage's Study Group</span>
              </Link>
              <UserMenu />
            </div>
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
                {/* Bookmark Button */}
                <button
                  onClick={toggleBookmark}
                  disabled={bookmarkLoading}
                  className={`flex items-center px-4 py-2 rounded-lg transition ${
                    isBookmarked
                      ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                      : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
                  }`}
                  title={user ? (isBookmarked ? 'Remove bookmark' : 'Bookmark this case') : 'Login to bookmark'}
                >
                  {bookmarkLoading ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Bookmark className={`h-4 w-4 mr-2 ${isBookmarked ? 'fill-current' : ''}`} />
                  )}
                  {isBookmarked ? 'Bookmarked' : 'Bookmark'}
                </button>

                {/* Add to Collection Dropdown */}
                <div className="relative" ref={dropdownRef}>
                  <button
                    onClick={() => {
                      if (!user) {
                        router.push('/login')
                        return
                      }
                      setShowCollectionDropdown(!showCollectionDropdown)
                    }}
                    className="flex items-center px-4 py-2 bg-neutral-100 hover:bg-neutral-200 rounded-lg text-neutral-700"
                  >
                    <FolderPlus className="h-4 w-4 mr-2" />
                    Add to Collection
                    <ChevronDown className={`h-4 w-4 ml-1 transition ${showCollectionDropdown ? 'rotate-180' : ''}`} />
                  </button>

                  {showCollectionDropdown && (
                    <div className="absolute top-full left-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-neutral-200 py-2 z-50">
                      {collections.length === 0 ? (
                        <div className="px-4 py-3 text-sm text-neutral-500">
                          <p>No collections yet</p>
                          <Link
                            href="/library"
                            className="text-blue-600 hover:text-blue-700 font-medium"
                            onClick={() => setShowCollectionDropdown(false)}
                          >
                            Create one in My Library
                          </Link>
                        </div>
                      ) : (
                        <>
                          <div className="px-4 py-2 text-xs font-medium text-neutral-500 uppercase tracking-wide border-b">
                            Your Collections
                          </div>
                          {collections.map(collection => (
                            <button
                              key={collection.id}
                              onClick={() => toggleCollection(collection.id)}
                              disabled={addingToCollection === collection.id}
                              className="w-full flex items-center justify-between px-4 py-2 hover:bg-neutral-50 text-left"
                            >
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-neutral-900 truncate">{collection.name}</p>
                                {collection.subject && (
                                  <p className="text-xs text-neutral-500">{collection.subject}</p>
                                )}
                              </div>
                              {addingToCollection === collection.id ? (
                                <Loader2 className="h-4 w-4 animate-spin text-neutral-400 flex-shrink-0" />
                              ) : caseInCollections.has(collection.id) ? (
                                <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                              ) : null}
                            </button>
                          ))}
                          <div className="border-t mt-2 pt-2">
                            <Link
                              href="/library"
                              className="flex items-center px-4 py-2 text-sm text-blue-600 hover:bg-blue-50"
                              onClick={() => setShowCollectionDropdown(false)}
                            >
                              <FolderPlus className="h-4 w-4 mr-2" />
                              Create New Collection
                            </Link>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>

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
                  <div className="prose prose-sm max-w-none space-y-4">
                    {caseSummary.summary.split('\n').map((line, idx) => {
                      // Main title (# Header)
                      if (line.trim().match(/^#\s+[^#]/)) {
                        const headerText = line.replace(/^#\s+/, '').trim()
                        return (
                          <h3 key={idx} className="text-xl font-bold text-neutral-900 mb-4">
                            {headerText}
                          </h3>
                        )
                      }
                      // Section headers (## 📋 Facts or **📋 Facts**)
                      else if (line.trim().match(/^##\s+[📋⚖️📚💡🎯]/) || line.trim().match(/^\*\*[📋⚖️📚💡🎯]/)) {
                        const headerText = line.replace(/^##\s+/, '').replace(/\*\*/g, '').trim()
                        return (
                          <div key={idx} className="mt-6 first:mt-0">
                            <h4 className="text-lg font-bold text-neutral-900 mb-2 flex items-center">
                              {headerText}
                            </h4>
                          </div>
                        )
                      }
                      // Numbered list items
                      else if (line.trim().match(/^\d+\.\s+/)) {
                        const itemText = line.trim()
                        return (
                          <p key={idx} className="text-neutral-700 leading-relaxed ml-4">
                            {itemText}
                          </p>
                        )
                      }
                      // Bold text without emoji
                      else if (line.includes('**')) {
                        const parts = line.split('**').filter(p => p.trim())
                        return (
                          <div key={idx} className="mb-2">
                            {parts.map((part, i) => (
                              i % 2 === 0 ? (
                                <span key={i} className="text-neutral-700">{part}</span>
                              ) : (
                                <strong key={i} className="font-semibold text-neutral-900">{part}</strong>
                              )
                            ))}
                          </div>
                        )
                      }
                      // Regular paragraphs
                      else if (line.trim()) {
                        return (
                          <p key={idx} className="text-neutral-700 leading-relaxed">
                            {line.trim()}
                          </p>
                        )
                      }
                      return null
                    })}
                  </div>

                  {/* Token usage and cost info */}
                  <div className="mt-6 pt-4 border-t border-neutral-200 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-4 text-neutral-600">
                      <span>🤖 Generated by {caseSummary.model || 'Claude'}</span>
                      {caseSummary.tokens_used && (
                        <span className="text-neutral-500">
                          {caseSummary.tokens_used.total.toLocaleString()} tokens
                        </span>
                      )}
                    </div>
                    <div className="text-neutral-600">
                      Cost: ${caseSummary.cost.toFixed(4)}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-neutral-600 mb-4">
                    Generate an AI-powered case brief with:
                  </p>
                  <div className="grid grid-cols-2 gap-3 max-w-md mx-auto text-sm text-neutral-700">
                    <div className="flex items-center">
                      <span className="mr-2">📋</span>
                      <span>Key Facts</span>
                    </div>
                    <div className="flex items-center">
                      <span className="mr-2">⚖️</span>
                      <span>Legal Issues</span>
                    </div>
                    <div className="flex items-center">
                      <span className="mr-2">📚</span>
                      <span>Court Holding</span>
                    </div>
                    <div className="flex items-center">
                      <span className="mr-2">💡</span>
                      <span>Reasoning</span>
                    </div>
                    <div className="flex items-center col-span-2 justify-center">
                      <span className="mr-2">🎯</span>
                      <span>Significance</span>
                    </div>
                  </div>
                  <p className="text-xs text-neutral-500 mt-4">
                    Estimated cost: $0.001 - $0.003 per brief
                  </p>
                </div>
              )}
            </div>

            {/* Comments Section */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <Comments caseId={caseData.id} />
            </div>

            {/* Case Text */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-neutral-900">Full Opinion</h2>
                {caseData.pdf_url && (
                  <a
                    href={caseData.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    View PDF
                  </a>
                )}
              </div>

              {caseData.content && caseData.content.length > 50 ? (
                <div>
                  {/* Show preview notice if content is truncated */}
                  {caseData.content.length < 5000 && caseData.pdf_url && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 text-sm">
                      <AlertCircle className="h-4 w-4 inline mr-2 text-amber-600" />
                      <span className="text-amber-900">
                        This is a preview. <a href={caseData.pdf_url} target="_blank" rel="noopener noreferrer" className="underline font-medium">View the full opinion PDF</a> for complete text.
                      </span>
                    </div>
                  )}

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

                  {/* PDF Embed Option */}
                  {caseData.pdf_url && (
                    <div className="mt-6 border-t pt-6">
                      <details className="group">
                        <summary className="cursor-pointer text-sm font-medium text-neutral-700 hover:text-neutral-900 flex items-center">
                          <FileText className="h-4 w-4 mr-2 text-neutral-500" />
                          View PDF inline
                          <span className="ml-2 text-neutral-400 group-open:rotate-180 transition-transform">▼</span>
                        </summary>
                        <div className="mt-4">
                          <iframe
                            src={caseData.pdf_url}
                            className="w-full border rounded-lg"
                            style={{ height: '800px' }}
                            title="Case Opinion PDF"
                          />
                        </div>
                      </details>
                    </div>
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
                    {caseData.pdf_url ? ' Please view the PDF version.' : ' Please view the full case on CourtListener.'}
                  </p>
                  {caseData.pdf_url ? (
                    <a
                      href={caseData.pdf_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition"
                    >
                      <FileText className="h-5 w-5 mr-2" />
                      View Full Opinion PDF
                    </a>
                  ) : (
                    (() => {
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
                    })()
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar - Right 1/3 */}
          <div className="space-y-6">
            {/* Citation Network Panel */}
            {citations && (citations.citing_count > 0 || citations.cited_count > 0) && (
              <div className="bg-white rounded-lg shadow-sm border p-4">
                <h3 className="text-md font-semibold text-neutral-900 mb-4 flex items-center">
                  <Scale className="h-4 w-4 mr-2 text-purple-600" />
                  Citation Network
                </h3>

                {/* Cases Citing This Case */}
                {citations.citing_cases.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-neutral-700 mb-2 flex items-center">
                      <TrendingUp className="h-3 w-3 mr-1 text-green-600" />
                      Cited By ({citations.citing_count})
                    </h4>
                    <div className="space-y-2">
                      {citations.citing_cases.map((c) => (
                        <Link
                          key={c.id}
                          href={`/case/${c.id}`}
                          className="block p-2 hover:bg-neutral-50 rounded border border-transparent hover:border-neutral-200"
                        >
                          <p className="text-sm font-medium text-blue-600 hover:text-blue-700 line-clamp-2">
                            {c.title || c.case_name || 'Untitled Case'}
                          </p>
                          <p className="text-xs text-neutral-500 mt-1">
                            {c.court_name || 'Unknown Court'} {c.decision_date ? `• ${new Date(c.decision_date).getFullYear()}` : ''}
                          </p>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {/* Cases This Case Cites */}
                {citations.cited_cases.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-neutral-700 mb-2 flex items-center">
                      <Gavel className="h-3 w-3 mr-1 text-blue-600" />
                      Cites ({citations.cited_count})
                    </h4>
                    <div className="space-y-2">
                      {citations.cited_cases.map((c) => (
                        <Link
                          key={c.id}
                          href={`/case/${c.id}`}
                          className="block p-2 hover:bg-neutral-50 rounded border border-transparent hover:border-neutral-200"
                        >
                          <p className="text-sm font-medium text-blue-600 hover:text-blue-700 line-clamp-2">
                            {c.title || c.case_name || 'Untitled Case'}
                          </p>
                          <p className="text-xs text-neutral-500 mt-1">
                            {c.court_name || 'Unknown Court'} {c.decision_date ? `• ${new Date(c.decision_date).getFullYear()}` : ''}
                          </p>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
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
