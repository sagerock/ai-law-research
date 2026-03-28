'use client'

import { useState, useEffect, useRef } from 'react'
import { BookOpen, ChevronDown, ChevronUp, ChevronRight, Scale, FileText, Gavel, Search, Plus, X, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'
import { buildCanonicalUrl } from '@/lib/citationUrls'

interface LibraryDoc {
  id: number
  title: string
  doc_type: string
  jurisdiction: string | null
}

interface UserCase {
  id: number
  case_id: string
  title: string
  reporter_cite: string | null
  decision_date: string | null
  court_name: string | null
}

interface SearchResult {
  id: string
  title: string
  reporter_cite: string | null
  decision_date: string | null
  court_name: string | null
  has_brief: boolean
  citation_count: number
}

interface MSJResourcesProps {
  projectId: number
  jurisdiction?: string
}

// Core SJ cases that are always available (hard-coded IDs match the database)
const CORE_CASES = {
  procedural: [
    {
      id: '111722',
      title: 'Celotex Corp. v. Catrett',
      cite: '477 U.S. 317 (1986)',
      description: "Movant's burden on SJ; established the 'show me' (absence of evidence) motion",
    },
    {
      id: '111719',
      title: 'Anderson v. Liberty Lobby, Inc.',
      cite: '477 U.S. 242 (1986)',
      description: '"Genuine dispute" means a reasonable jury could find for the non-movant',
    },
    {
      id: '2672535',
      title: 'Tolan v. Cotton',
      cite: '572 U.S. 650 (2014)',
      description: 'Court must draw all reasonable inferences in favor of the non-movant',
    },
  ],
  ohio_substantive: [
    {
      id: '10686709',
      title: 'Dresher v. Burt',
      cite: '75 Ohio St.3d 280 (1996)',
      description: "Ohio's leading SJ burden case: movant must point to specific evidence showing opponent lacks proof",
    },
    {
      id: '4025863',
      title: 'Mudrich v. Standard Oil Co.',
      cite: '153 Ohio St. 31 (1950)',
      description: 'Intervening cause does not break causation if reasonably foreseeable',
    },
    {
      id: '6867332',
      title: 'Cascone v. Herb Kay Co.',
      cite: '6 Ohio St.3d 155 (1983)',
      description: 'Two-part test for superseding cause; foreseeability question is for the jury',
    },
    {
      id: '6876097',
      title: 'Leibreich v. A.J. Refrigeration, Inc.',
      cite: '67 Ohio St.3d 266 (1993)',
      description: 'Superseding cause is a defense to both negligence and strict liability',
    },
  ],
}

export default function MSJResources({ projectId, jurisdiction }: MSJResourcesProps) {
  const { session } = useAuth()
  const [expanded, setExpanded] = useState(false)
  const [libraryDocs, setLibraryDocs] = useState<LibraryDoc[]>([])
  const [userCases, setUserCases] = useState<UserCase[]>([])
  const [searchText, setSearchText] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [addingCaseId, setAddingCaseId] = useState<string | null>(null)
  const [removingCaseId, setRemovingCaseId] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/api/v1/msj/library`)
      .then((r) => r.json())
      .then(setLibraryDocs)
      .catch(() => {})
  }, [])

  const fetchUserCases = () => {
    if (!session?.access_token) return
    fetch(`${API_URL}/api/v1/msj/projects/${projectId}/cases`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    })
      .then((r) => r.json())
      .then((data) => setUserCases(data.cases || []))
      .catch(() => {})
  }

  useEffect(() => {
    fetchUserCases()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, session])

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (searchText.trim().length < 2) {
      setSearchResults([])
      setSearching(false)
      return
    }

    setSearching(true)
    debounceRef.current = setTimeout(() => {
      fetch(`${API_URL}/api/v1/search-cases?q=${encodeURIComponent(searchText.trim())}&limit=5`)
        .then((r) => r.json())
        .then((data) => {
          setSearchResults(data.cases || [])
        })
        .catch(() => setSearchResults([]))
        .finally(() => setSearching(false))
    }, 350)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [searchText])

  const handleAddCase = async (caseId: string) => {
    if (!session?.access_token) return
    setAddingCaseId(caseId)
    try {
      await fetch(`${API_URL}/api/v1/msj/projects/${projectId}/cases`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ case_id: caseId }),
      })
      fetchUserCases()
    } catch {
      // silent
    } finally {
      setAddingCaseId(null)
    }
  }

  const handleRemoveCase = async (caseId: string) => {
    if (!session?.access_token) return
    setRemovingCaseId(caseId)
    try {
      await fetch(`${API_URL}/api/v1/msj/projects/${projectId}/cases/${caseId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      setUserCases((prev) => prev.filter((c) => c.case_id !== caseId))
    } catch {
      // silent
    } finally {
      setRemovingCaseId(null)
    }
  }

  const addedCaseIds = new Set(userCases.map((c) => c.case_id))

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6 mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
            <BookOpen className="h-5 w-5 text-sage-700" />
          </div>
          <div className="text-left">
            <h2 className="text-lg font-medium text-stone-900">Approved Sources</h2>
            <p className="text-sm text-stone-500">
              Cases, rules, and resources the AI can cite in your motion
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-stone-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-stone-400" />
        )}
      </button>

      {expanded && (
        <div className="mt-5 space-y-5">
          {/* Procedural cases */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Scale className="h-4 w-4 text-sage-600" />
              <h3 className="text-sm font-medium text-stone-700">
                Summary Judgment Standard (Federal)
              </h3>
            </div>
            <div className="space-y-2">
              {CORE_CASES.procedural.map((c) => (
                <Link
                  key={c.id}
                  href={buildCanonicalUrl(c.cite, c.title)}
                  className="block p-3 bg-stone-50 rounded-lg hover:bg-sage-50 transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-sm font-medium text-stone-800 group-hover:text-sage-800">
                        {c.title}
                      </span>
                      <span className="text-xs text-stone-500 ml-1">{c.cite}</span>
                      <p className="text-xs text-stone-500 mt-0.5">{c.description}</p>
                    </div>
                    <ChevronRight className="h-3.5 w-3.5 text-stone-300 group-hover:text-sage-500 flex-shrink-0 mt-0.5" />
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Ohio substantive cases — only shown when jurisdiction is ohio */}
          {jurisdiction === 'ohio' && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Gavel className="h-4 w-4 text-sage-600" />
                <h3 className="text-sm font-medium text-stone-700">
                  Ohio Superseding Cause Doctrine
                </h3>
              </div>
              <div className="space-y-2">
                {CORE_CASES.ohio_substantive.map((c) => (
                  <Link
                    key={c.id}
                    href={buildCanonicalUrl(c.cite, c.title)}
                    className="block p-3 bg-stone-50 rounded-lg hover:bg-sage-50 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="text-sm font-medium text-stone-800 group-hover:text-sage-800">
                          {c.title}
                        </span>
                        <span className="text-xs text-stone-500 ml-1">{c.cite}</span>
                        <p className="text-xs text-stone-500 mt-0.5">{c.description}</p>
                      </div>
                      <ChevronRight className="h-3.5 w-3.5 text-stone-300 group-hover:text-sage-500 flex-shrink-0 mt-0.5" />
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Rule 56 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-sage-600" />
              <h3 className="text-sm font-medium text-stone-700">Rules</h3>
            </div>
            <Link
              href="/rules/rule-56"
              className="block p-3 bg-stone-50 rounded-lg hover:bg-sage-50 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-sm font-medium text-stone-800 group-hover:text-sage-800">
                    Fed. R. Civ. P. 56
                  </span>
                  <span className="text-xs text-stone-500 ml-1">Summary Judgment</span>
                  <p className="text-xs text-stone-500 mt-0.5">
                    The procedural rule governing motions for summary judgment in federal court
                  </p>
                </div>
                <ChevronRight className="h-3.5 w-3.5 text-stone-300 group-hover:text-sage-500 flex-shrink-0 mt-0.5" />
              </div>
            </Link>
          </div>

          {/* User-added cases */}
          {userCases.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="h-4 w-4 text-sage-600" />
                <h3 className="text-sm font-medium text-stone-700">
                  Your Added Cases ({userCases.length})
                </h3>
              </div>
              <div className="space-y-2">
                {userCases.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-start gap-2 p-3 bg-stone-50 rounded-lg group"
                  >
                    <Link
                      href={buildCanonicalUrl(c.reporter_cite, c.title)}
                      className="flex-1 min-w-0 hover:opacity-80 transition-opacity"
                    >
                      <span className="text-sm font-medium text-stone-800 block truncate">
                        {c.title}
                      </span>
                      {(c.reporter_cite || c.court_name) && (
                        <span className="text-xs text-stone-500">
                          {c.reporter_cite || c.court_name}
                        </span>
                      )}
                    </Link>
                    <button
                      onClick={() => handleRemoveCase(c.case_id)}
                      disabled={removingCaseId === c.case_id}
                      className="flex-shrink-0 p-1 text-stone-300 hover:text-red-400 transition-colors rounded disabled:opacity-40"
                      title="Remove case"
                    >
                      {removingCaseId === c.case_id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <X className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search & Add Cases */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Search className="h-4 w-4 text-sage-600" />
              <h3 className="text-sm font-medium text-stone-700">Search & Add Cases</h3>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400 pointer-events-none" />
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search by case name or citation..."
                className="w-full pl-9 pr-4 py-2.5 text-sm border border-stone-200 rounded-lg
                           bg-stone-50 focus:bg-white focus:border-sage-400 focus:outline-none
                           focus:ring-2 focus:ring-sage-100 transition-colors"
              />
              {searching && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400 animate-spin" />
              )}
            </div>

            {/* Search results */}
            {searchText.trim().length >= 2 && !searching && (
              <div className="mt-2 space-y-1">
                {searchResults.length === 0 ? (
                  <p className="text-xs text-stone-400 px-1 py-2">No results found.</p>
                ) : (
                  searchResults.map((result) => {
                    const alreadyAdded = addedCaseIds.has(result.id)
                    return (
                      <div
                        key={result.id}
                        className="flex items-start gap-2 p-2.5 bg-stone-50 rounded-lg"
                      >
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-stone-800 block truncate">
                            {result.title}
                          </span>
                          {(result.reporter_cite || result.court_name) && (
                            <span className="text-xs text-stone-500">
                              {result.reporter_cite || result.court_name}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => !alreadyAdded && handleAddCase(result.id)}
                          disabled={alreadyAdded || addingCaseId === result.id}
                          className={`flex-shrink-0 flex items-center gap-1 px-2 py-1 rounded text-xs font-medium
                                      transition-colors disabled:opacity-40
                                      ${alreadyAdded
                                        ? 'bg-sage-100 text-sage-600 cursor-default'
                                        : 'bg-sage-700 text-white hover:bg-sage-600'
                                      }`}
                          title={alreadyAdded ? 'Already added' : 'Add to approved sources'}
                        >
                          {addingCaseId === result.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : alreadyAdded ? (
                            'Added'
                          ) : (
                            <>
                              <Plus className="h-3 w-3" />
                              Add
                            </>
                          )}
                        </button>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>

          {/* Library resources */}
          {libraryDocs.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="h-4 w-4 text-sage-600" />
                <h3 className="text-sm font-medium text-stone-700">
                  Reference Library ({libraryDocs.length} resources)
                </h3>
              </div>
              <div className="space-y-1">
                {libraryDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 px-3 py-2 text-xs text-stone-600 bg-stone-50 rounded"
                  >
                    <span className="px-1.5 py-0.5 bg-stone-200 text-stone-500 rounded text-[10px]">
                      {doc.doc_type}
                    </span>
                    <span className="truncate">{doc.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
