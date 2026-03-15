'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Calendar, FileText, TrendingUp, Scale, ExternalLink, Copy, CheckCircle, Sparkles, AlertCircle, BookOpen, Gavel, Loader2, Bookmark, FolderPlus, Check, ChevronDown, ThumbsUp, ThumbsDown } from 'lucide-react'
import { API_URL } from '@/lib/api'
import { parseLegalCitations, extractLegalTextRefs } from '@/lib/legalCitations'
import Header from '@/components/Header'
import { useAuth } from '@/lib/auth-context'
import Comments from '@/components/Comments'
import CaseAskAI from '@/components/CaseAskAI'

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
  is_stub?: boolean
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
  ratings?: {
    thumbs_up: number
    thumbs_down: number
    user_rating: number | null
  }
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
  const searchParams = useSearchParams()
  const { user, session } = useAuth()
  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null)
  const [citations, setCitations] = useState<CitationData | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [copiedCitation, setCopiedCitation] = useState(false)

  // Collection back-navigation context
  const collectionId = searchParams.get('collection')
  const sharedCollectionId = searchParams.get('shared_collection')
  const [collectionName, setCollectionName] = useState<string | null>(null)

  // Summary rating state
  const [summaryRating, setSummaryRating] = useState<number | null>(null)
  const [thumbsUp, setThumbsUp] = useState(0)
  const [thumbsDown, setThumbsDown] = useState(0)
  const [ratingLoading, setRatingLoading] = useState(false)

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

  // Re-fetch user's summary rating when session becomes available
  useEffect(() => {
    if (session?.access_token && caseSummary) {
      fetchCachedSummary()
    }
  }, [session?.access_token])

  // Fetch library data when user is logged in
  useEffect(() => {
    if (user && session?.access_token) {
      checkBookmarkStatus()
      fetchUserCollections()
    }
  }, [user, session, caseId])

  // Fetch collection name for back-navigation breadcrumb
  useEffect(() => {
    if (collectionId && session?.access_token) {
      fetch(`${API_URL}/api/v1/library/collections/${collectionId}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data?.name) setCollectionName(data.name) })
        .catch(() => {})
    } else if (sharedCollectionId) {
      fetch(`${API_URL}/api/v1/shared/${sharedCollectionId}`)
        .then(r => r.ok ? r.json() : null)
        .then(data => { if (data?.name) setCollectionName(data.name) })
        .catch(() => {})
    }
  }, [collectionId, sharedCollectionId, session?.access_token])

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
      const headers: Record<string, string> = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/summary`, { headers })
      if (!response.ok) return
      const data = await response.json()
      if (data.ratings) {
        setThumbsUp(data.ratings.thumbs_up)
        setThumbsDown(data.ratings.thumbs_down)
        setSummaryRating(data.ratings.user_rating)
      }
      if (data.cached && data.summary) {
        setCaseSummary(data)
        console.log('Loaded cached summary')
      }
    } catch (err) {
      console.log('No cached summary available')
    }
  }

  const rateSummary = async (rating: number) => {
    if (!session?.access_token) return
    setRatingLoading(true)
    try {
      // Toggle off if clicking same rating
      const newRating = summaryRating === rating ? 0 : rating
      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/summary/rate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ rating: newRating })
      })
      if (response.ok) {
        const data = await response.json()
        setThumbsUp(data.thumbs_up)
        setThumbsDown(data.thumbs_down)
        setSummaryRating(data.user_rating)
      }
    } catch (err) {
      console.error('Failed to rate summary:', err)
    } finally {
      setRatingLoading(false)
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

  const [summaryError, setSummaryError] = useState<string | null>(null)
  const [localCaseData, setLocalCaseData] = useState(caseData)

  const generateSummary = async () => {
    setSummaryLoading(true)
    setSummaryError(null)
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }
      // Send auth header (required for stub cases, optional for others)
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }

      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/summarize`, {
        method: 'POST',
        headers,
      })
      if (response.status === 401) {
        setSummaryError('sign_in_required')
        return
      }
      if (response.status === 402) {
        setSummaryError('pool_empty')
        return
      }
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to generate summary')
      }
      const data = await response.json()
      setCaseSummary(data)

      // If this was a stub case, refresh case data (content is now populated)
      if (localCaseData.is_stub) {
        try {
          const caseResp = await fetch(`${API_URL}/api/v1/cases/${caseId}`)
          if (caseResp.ok) {
            const refreshed = await caseResp.json()
            setLocalCaseData(refreshed)
          }
        } catch {
          // Non-critical, page still works
        }
      }
    } catch (err: any) {
      console.error('Failed to generate summary:', err)
      setSummaryError(err.message || 'Failed to generate summary')
    } finally {
      setSummaryLoading(false)
    }
  }

  const handleCopy = () => {
    if (localCaseData?.content) {
      navigator.clipboard.writeText(localCaseData.content)
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
    <div className="min-h-screen bg-cream">
      <Header />

      {/* Case Content */}
      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Back to collection breadcrumb */}
        {(collectionId || sharedCollectionId) && (
          <div className="mb-4">
            <Link
              href={collectionId ? `/library?collection=${collectionId}` : `/shared/${sharedCollectionId}`}
              className="inline-flex items-center gap-1.5 text-sm text-sage-600 hover:text-sage-700 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              {collectionName ? `Back to ${collectionName}` : 'Back to collection'}
            </Link>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content - Left 2/3 */}
          <div className="lg:col-span-2 space-y-6">
            {/* Case Header */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h1 className="text-2xl font-bold text-stone-900 mb-4">
                {caseData.title || caseData.case_name}
              </h1>

              {/* Case Metadata */}
              <div className="flex flex-wrap items-center gap-4 text-sm text-stone-600 mb-4">
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
                <div className="bg-sage-50 text-sage-700 px-3 py-2 rounded inline-block mb-4">
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
                      : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
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
                    className="flex items-center px-4 py-2 bg-stone-100 hover:bg-stone-200 rounded-lg text-stone-700"
                  >
                    <FolderPlus className="h-4 w-4 mr-2" />
                    Add to Collection
                    <ChevronDown className={`h-4 w-4 ml-1 transition ${showCollectionDropdown ? 'rotate-180' : ''}`} />
                  </button>

                  {showCollectionDropdown && (
                    <div className="absolute top-full left-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-stone-200 py-2 z-50">
                      {collections.length === 0 ? (
                        <div className="px-4 py-3 text-sm text-stone-500">
                          <p>No collections yet</p>
                          <Link
                            href="/library"
                            className="text-sage-600 hover:text-sage-700 font-medium"
                            onClick={() => setShowCollectionDropdown(false)}
                          >
                            Create one in My Library
                          </Link>
                        </div>
                      ) : (
                        <>
                          <div className="px-4 py-2 text-xs font-medium text-stone-500 uppercase tracking-wide border-b">
                            Your Collections
                          </div>
                          {collections.map(collection => (
                            <button
                              key={collection.id}
                              onClick={() => toggleCollection(collection.id)}
                              disabled={addingToCollection === collection.id}
                              className="w-full flex items-center justify-between px-4 py-2 hover:bg-stone-50 text-left"
                            >
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-stone-900 truncate">{collection.name}</p>
                                {collection.subject && (
                                  <p className="text-xs text-stone-500">{collection.subject}</p>
                                )}
                              </div>
                              {addingToCollection === collection.id ? (
                                <Loader2 className="h-4 w-4 animate-spin text-stone-400 flex-shrink-0" />
                              ) : caseInCollections.has(collection.id) ? (
                                <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                              ) : null}
                            </button>
                          ))}
                          <div className="border-t mt-2 pt-2">
                            <Link
                              href="/library"
                              className="flex items-center px-4 py-2 text-sm text-sage-600 hover:bg-sage-50"
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

                {!localCaseData.is_stub && (
                  <button
                    onClick={handleCopy}
                    className="flex items-center px-4 py-2 bg-stone-100 hover:bg-stone-200 rounded-lg text-stone-700"
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
                )}
                <button
                  onClick={handleCopyCitation}
                  className="flex items-center px-4 py-2 bg-stone-100 hover:bg-stone-200 rounded-lg text-stone-700"
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
                <a
                  href={`https://www.courtlistener.com/?q=id%3A${caseId}&type=o`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center px-4 py-2 bg-sage-700 hover:bg-sage-600 text-white rounded-lg"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View on CourtListener
                </a>
              </div>
            </div>

            {/* Stub Case Banner */}
            {localCaseData.is_stub && !caseSummary && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-5">
                <div className="flex items-start gap-3">
                  <BookOpen className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-amber-900 font-medium mb-1">
                      This case is cited by {localCaseData.metadata?.citation_count || 'other'} case{(localCaseData.metadata?.citation_count || 0) !== 1 ? 's' : ''} in our database but doesn&apos;t have a brief yet.
                    </p>
                    <p className="text-amber-800 text-sm mb-3">
                      Generate an AI brief to get the full case analysis. The opinion text will be fetched from CourtListener automatically.
                    </p>
                    {!user ? (
                      <Link
                        href="/login"
                        className="inline-flex items-center px-4 py-2 bg-sage-700 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition"
                      >
                        <Sparkles className="h-4 w-4 mr-2" />
                        Sign in to Generate AI Brief
                      </Link>
                    ) : (
                      <button
                        onClick={generateSummary}
                        disabled={summaryLoading}
                        className="inline-flex items-center px-4 py-2 bg-sage-700 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition disabled:bg-neutral-400"
                      >
                        {summaryLoading ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Fetching opinion &amp; generating brief...
                          </>
                        ) : (
                          <>
                            <Sparkles className="h-4 w-4 mr-2" />
                            Generate AI Brief
                          </>
                        )}
                      </button>
                    )}
                    {summaryError === 'sign_in_required' && (
                      <p className="text-red-600 text-sm mt-2">Please sign in to generate briefs for this case.</p>
                    )}
                    {summaryError === 'pool_empty' && (
                      <p className="text-red-600 text-sm mt-2">
                        The community AI pool is empty.{' '}
                        <a href="/transparency" className="underline">Donate to refill it</a> or{' '}
                        <a href="/byok" className="underline">add your own API key</a> for unlimited access.
                      </p>
                    )}
                    {summaryError && summaryError !== 'sign_in_required' && summaryError !== 'pool_empty' && (
                      <p className="text-red-600 text-sm mt-2">{summaryError}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* AI Summary */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-stone-900 flex items-center">
                  <Sparkles className="h-5 w-5 mr-2 text-sage-600" />
                  AI Case Brief
                </h2>
                {!caseSummary && !localCaseData.is_stub && (
                  <button
                    onClick={generateSummary}
                    disabled={summaryLoading}
                    className="flex items-center px-3 py-1.5 bg-sage-700 hover:bg-purple-700 text-white rounded-lg text-sm disabled:bg-neutral-400"
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
                    {(() => {
                      // Render inline **bold**, *italic*, and legal citation links
                      const renderMarkdown = (text: string, keyPrefix: string = '') => {
                        const parts: React.ReactNode[] = []
                        const re = /(\*\*(.+?)\*\*|\*(.+?)\*)/g
                        let last = 0
                        let match: RegExpExecArray | null
                        while ((match = re.exec(text)) !== null) {
                          if (match.index > last) parts.push(text.slice(last, match.index))
                          if (match[2]) {
                            parts.push(<strong key={`${keyPrefix}b${match.index}`} className="font-semibold text-stone-900">{match[2]}</strong>)
                          } else if (match[3]) {
                            parts.push(<em key={`${keyPrefix}i${match.index}`}>{match[3]}</em>)
                          }
                          last = match.index + match[0].length
                        }
                        if (last < text.length) parts.push(text.slice(last))
                        return parts.length > 0 ? parts : [text]
                      }

                      const renderInline = (text: string): React.ReactNode[] => {
                        // First pass: detect legal citations and split into segments
                        const segments = parseLegalCitations(text)
                        if (segments.length === 1 && !segments[0].href) {
                          return renderMarkdown(text)
                        }
                        // Second pass: apply markdown to each segment, wrap linked ones in <Link>
                        const result: React.ReactNode[] = []
                        segments.forEach((seg, si) => {
                          if (seg.href) {
                            result.push(
                              <Link key={`cite-${si}`} href={seg.href}
                                className="text-sage-600 hover:text-sage-800 underline decoration-purple-300 hover:decoration-purple-500 transition-colors">
                                {seg.text}
                              </Link>
                            )
                          } else {
                            result.push(...renderMarkdown(seg.text, `s${si}-`))
                          }
                        })
                        return result
                      }

                      return caseSummary.summary.split('\n').map((line, idx) => {
                      // Main title (# Header)
                      if (line.trim().match(/^#\s+[^#]/)) {
                        const headerText = line.replace(/^#\s+/, '').trim()
                        return (
                          <h3 key={idx} className="text-xl font-bold text-stone-900 mb-4">
                            {headerText}
                          </h3>
                        )
                      }
                      // Section headers (## 📋 Facts or **📋 Facts**)
                      else if (line.trim().match(/^##\s+[📋⚖️📚💡🎯]/) || line.trim().match(/^\*\*[📋⚖️📚💡🎯]/)) {
                        const headerText = line.replace(/^##\s+/, '').replace(/\*\*/g, '').trim()
                        return (
                          <div key={idx} className="mt-6 first:mt-0">
                            <h4 className="text-lg font-bold text-stone-900 mb-2 flex items-center">
                              {headerText}
                            </h4>
                          </div>
                        )
                      }
                      // Numbered list items
                      else if (line.trim().match(/^\d+\.\s+/)) {
                        return (
                          <p key={idx} className="text-stone-700 leading-relaxed ml-4">
                            {renderInline(line.trim())}
                          </p>
                        )
                      }
                      // Regular paragraphs (handles inline bold/italic)
                      else if (line.trim()) {
                        return (
                          <p key={idx} className="text-stone-700 leading-relaxed">
                            {renderInline(line.trim())}
                          </p>
                        )
                      }
                      return null
                    })})()}

                  </div>

                  {/* Rating + Token usage and cost info */}
                  <div className="mt-6 pt-4 border-t border-stone-200 space-y-3">
                    {/* Was this helpful? */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 text-sm">
                        <span className="text-stone-500">Was this helpful?</span>
                        <button
                          onClick={() => rateSummary(1)}
                          disabled={ratingLoading || !session?.access_token}
                          title={!session?.access_token ? 'Sign in to rate' : summaryRating === 1 ? 'Remove rating' : 'Helpful'}
                          className={`flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
                            summaryRating === 1
                              ? 'bg-green-100 text-green-700'
                              : 'text-stone-400 hover:text-green-600 hover:bg-green-50'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          <ThumbsUp className="h-4 w-4" />
                          {thumbsUp > 0 && <span className="text-xs">{thumbsUp}</span>}
                        </button>
                        <button
                          onClick={() => rateSummary(-1)}
                          disabled={ratingLoading || !session?.access_token}
                          title={!session?.access_token ? 'Sign in to rate' : summaryRating === -1 ? 'Remove rating' : 'Not helpful'}
                          className={`flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
                            summaryRating === -1
                              ? 'bg-red-100 text-red-700'
                              : 'text-stone-400 hover:text-red-600 hover:bg-red-50'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          <ThumbsDown className="h-4 w-4" />
                          {thumbsDown > 0 && <span className="text-xs">{thumbsDown}</span>}
                        </button>
                      </div>
                    </div>
                    {/* Model info + cost */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-4 text-stone-600">
                        <span>🤖 Generated by {caseSummary.model || 'Claude'}</span>
                        {caseSummary.tokens_used && (
                          <span className="text-stone-500">
                            {caseSummary.tokens_used.total.toLocaleString()} tokens
                          </span>
                        )}
                      </div>
                      <div className="text-stone-600">
                        Cost: ${caseSummary.cost.toFixed(4)}
                      </div>
                    </div>
                  </div>

                  {/* Referenced Legal Texts */}
                  {(() => {
                    const refs = extractLegalTextRefs(caseSummary.summary)
                    if (refs.length === 0) return null
                    const rules = refs.filter(r => r.type === 'rule')
                    const statutes = refs.filter(r => r.type === 'statute')
                    const constitution = refs.filter(r => r.type === 'constitution')
                    const groups = [
                      { label: 'Rules', items: rules },
                      { label: 'Statutes', items: statutes },
                      { label: 'Constitution', items: constitution },
                    ].filter(g => g.items.length > 0)
                    return (
                      <div className="mt-4 pt-4 border-t border-stone-200">
                        <h4 className="text-sm font-semibold text-stone-700 mb-3">Referenced Legal Texts</h4>
                        <div className="space-y-2">
                          {groups.map(group => (
                            <div key={group.label} className="flex flex-wrap items-center gap-2">
                              <span className="text-xs font-medium text-stone-500 w-20 shrink-0">{group.label}</span>
                              {group.items.map(ref => (
                                <Link
                                  key={ref.href}
                                  href={ref.href}
                                  className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-sage-50 text-sage-700 hover:bg-sage-50 transition-colors"
                                >
                                  {ref.label}
                                </Link>
                              ))}
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })()}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-stone-600 mb-4">
                    Generate an AI-powered case brief with:
                  </p>
                  <div className="grid grid-cols-2 gap-3 max-w-md mx-auto text-sm text-stone-700">
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
                  <p className="text-xs text-stone-500 mt-4">
                    Estimated cost: $0.001 - $0.003 per brief
                  </p>
                </div>
              )}
            </div>

            {/* Ask AI About This Case */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <CaseAskAI caseId={caseId} caseTitle={caseData.title || caseData.case_name || 'this case'} />
            </div>

            {/* Comments Section */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <Comments caseId={caseData.id} />
            </div>

            {/* Case Text */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-stone-900">Full Opinion</h2>
                {localCaseData.pdf_url && (
                  <a
                    href={localCaseData.pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    View PDF
                  </a>
                )}
              </div>

              {localCaseData.content && localCaseData.content.length > 50 ? (
                <div>
                  {/* Show preview notice if content is truncated */}
                  {localCaseData.content.length < 5000 && localCaseData.pdf_url && (
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 text-sm">
                      <AlertCircle className="h-4 w-4 inline mr-2 text-amber-600" />
                      <span className="text-amber-900">
                        This is a preview. <a href={localCaseData.pdf_url} target="_blank" rel="noopener noreferrer" className="underline font-medium">View the full opinion PDF</a> for complete text.
                      </span>
                    </div>
                  )}

                  <div className="prose prose-neutral max-w-none">
                    {/* Check if content contains HTML tags */}
                    {localCaseData.content.includes('<') && localCaseData.content.includes('>') ? (
                      <div
                        className="text-sm leading-relaxed text-stone-700"
                        dangerouslySetInnerHTML={{ __html: localCaseData.content }}
                      />
                    ) : (
                      <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-stone-700">
                        {localCaseData.content}
                      </pre>
                    )}
                  </div>

                  {/* PDF Embed Option */}
                  {localCaseData.pdf_url && (
                    <div className="mt-6 border-t pt-6">
                      <details className="group">
                        <summary className="cursor-pointer text-sm font-medium text-stone-700 hover:text-stone-900 flex items-center">
                          <FileText className="h-4 w-4 mr-2 text-stone-500" />
                          View PDF inline
                          <span className="ml-2 text-stone-400 group-open:rotate-180 transition-transform">▼</span>
                        </summary>
                        <div className="mt-4">
                          <iframe
                            src={localCaseData.pdf_url}
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
                <div className="bg-sage-50 border border-sage-200 rounded-lg p-6 text-center">
                  <AlertCircle className="h-12 w-12 text-sage-600 mx-auto mb-3" />
                  <h3 className="text-lg font-semibold text-stone-900 mb-2">
                    Full Opinion Text Not Available
                  </h3>
                  <p className="text-stone-600 mb-4">
                    The complete opinion text is not available in our database.
                    {localCaseData.pdf_url ? ' Please view the PDF version.' : ' Please view the full case on CourtListener.'}
                  </p>
                  {localCaseData.pdf_url ? (
                    <a
                      href={localCaseData.pdf_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition"
                    >
                      <FileText className="h-5 w-5 mr-2" />
                      View Full Opinion PDF
                    </a>
                  ) : (
                    (() => {
                      return (
                        <a
                          href={`https://www.courtlistener.com/?q=id%3A${caseId}&type=o`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center px-6 py-3 bg-sage-700 hover:bg-sage-600 text-white rounded-lg font-medium transition"
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
                <h3 className="text-md font-semibold text-stone-900 mb-4 flex items-center">
                  <Scale className="h-4 w-4 mr-2 text-sage-600" />
                  Citation Network
                </h3>

                {/* Cases Citing This Case */}
                {citations.citing_cases.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-stone-700 mb-2 flex items-center">
                      <TrendingUp className="h-3 w-3 mr-1 text-green-600" />
                      Cited By ({citations.citing_count})
                    </h4>
                    <div className="space-y-2">
                      {citations.citing_cases.map((c) => (
                        <Link
                          key={c.id}
                          href={`/case/${c.id}`}
                          className="block p-2 hover:bg-stone-50 rounded border border-transparent hover:border-stone-200"
                        >
                          <p className="text-sm font-medium text-sage-600 hover:text-sage-700 line-clamp-2">
                            {c.title || c.case_name || 'Untitled Case'}
                          </p>
                          <p className="text-xs text-stone-500 mt-1">
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
                    <h4 className="text-sm font-medium text-stone-700 mb-2 flex items-center">
                      <Gavel className="h-3 w-3 mr-1 text-sage-600" />
                      Cites ({citations.cited_count})
                    </h4>
                    <div className="space-y-2">
                      {citations.cited_cases.map((c) => (
                        <Link
                          key={c.id}
                          href={`/case/${c.id}`}
                          className="block p-2 hover:bg-stone-50 rounded border border-transparent hover:border-stone-200"
                        >
                          <p className="text-sm font-medium text-sage-600 hover:text-sage-700 line-clamp-2">
                            {c.title || c.case_name || 'Untitled Case'}
                          </p>
                          <p className="text-xs text-stone-500 mt-1">
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
                <h3 className="text-md font-semibold text-stone-900 mb-3">Additional Information</h3>
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
                      <div key={key} className="pb-2 border-b border-stone-100 last:border-0">
                        <dt className="text-xs font-medium text-stone-500 uppercase tracking-wide mb-1">
                          {key.replace(/_/g, ' ')}
                        </dt>
                        <dd className="text-sm text-stone-900 break-words">
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
