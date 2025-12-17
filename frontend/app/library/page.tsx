'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import {
  Scale,
  FolderOpen,
  Bookmark,
  Plus,
  Share2,
  Trash2,
  Loader2,
  ChevronRight,
  Copy,
  Check,
  X,
  Edit2
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Collection {
  id: string
  name: string
  description: string | null
  subject: string | null
  is_public: boolean
  case_count: number
  created_at: string | null
}

interface CollectionDetail extends Collection {
  cases: CollectionCase[]
}

interface CollectionCase {
  collection_case_id: string
  id: string
  title: string
  decision_date: string | null
  reporter_cite: string | null
  court_name: string | null
  notes: string | null
  added_at: string | null
}

interface BookmarkItem {
  id: string
  case_id: string
  title: string
  decision_date: string | null
  reporter_cite: string | null
  court_name: string | null
  folder: string | null
  notes: string | null
  created_at: string | null
}

export default function LibraryPage() {
  const { user, session, isLoading: authLoading, isConfigured } = useAuth()
  const router = useRouter()

  const [activeTab, setActiveTab] = useState<'collections' | 'bookmarks'>('collections')
  const [collections, setCollections] = useState<Collection[]>([])
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([])
  const [selectedCollection, setSelectedCollection] = useState<CollectionDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Create collection modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newCollectionName, setNewCollectionName] = useState('')
  const [newCollectionDescription, setNewCollectionDescription] = useState('')
  const [newCollectionSubject, setNewCollectionSubject] = useState('')
  const [newCollectionPublic, setNewCollectionPublic] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  // Share link copy state
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Get auth headers
  const getAuthHeaders = (): Record<string, string> => {
    if (!session?.access_token) return {}
    return {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json'
    }
  }

  // Fetch collections
  const fetchCollections = async () => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections`, {
        headers: getAuthHeaders()
      })

      if (response.ok) {
        const data = await response.json()
        setCollections(data.collections)
      } else if (response.status === 401) {
        setError('Please log in to view your library')
      }
    } catch (err) {
      console.error('Failed to fetch collections:', err)
    }
  }

  // Fetch bookmarks
  const fetchBookmarks = async () => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/bookmarks`, {
        headers: getAuthHeaders()
      })

      if (response.ok) {
        const data = await response.json()
        setBookmarks(data.bookmarks)
      }
    } catch (err) {
      console.error('Failed to fetch bookmarks:', err)
    }
  }

  // Fetch collection details
  const fetchCollectionDetails = async (collectionId: string) => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections/${collectionId}`, {
        headers: getAuthHeaders()
      })

      if (response.ok) {
        const data = await response.json()
        setSelectedCollection(data)
      }
    } catch (err) {
      console.error('Failed to fetch collection details:', err)
    }
  }

  // Create collection
  const createCollection = async () => {
    if (!session?.access_token || !newCollectionName.trim()) return

    setIsCreating(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: newCollectionName.trim(),
          description: newCollectionDescription.trim() || null,
          subject: newCollectionSubject.trim() || null,
          is_public: newCollectionPublic
        })
      })

      if (response.ok) {
        setShowCreateModal(false)
        setNewCollectionName('')
        setNewCollectionDescription('')
        setNewCollectionSubject('')
        setNewCollectionPublic(false)
        fetchCollections()
      }
    } catch (err) {
      console.error('Failed to create collection:', err)
    } finally {
      setIsCreating(false)
    }
  }

  // Delete collection
  const deleteCollection = async (collectionId: string) => {
    if (!session?.access_token) return
    if (!confirm('Are you sure you want to delete this collection?')) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections/${collectionId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })

      if (response.ok) {
        setCollections(prev => prev.filter(c => c.id !== collectionId))
        if (selectedCollection?.id === collectionId) {
          setSelectedCollection(null)
        }
      }
    } catch (err) {
      console.error('Failed to delete collection:', err)
    }
  }

  // Remove case from collection
  const removeCaseFromCollection = async (collectionId: string, caseId: string) => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections/${collectionId}/cases/${caseId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })

      if (response.ok && selectedCollection) {
        setSelectedCollection({
          ...selectedCollection,
          cases: selectedCollection.cases.filter(c => c.id !== caseId)
        })
        // Update count in list
        setCollections(prev => prev.map(c =>
          c.id === collectionId ? { ...c, case_count: c.case_count - 1 } : c
        ))
      }
    } catch (err) {
      console.error('Failed to remove case:', err)
    }
  }

  // Delete bookmark
  const deleteBookmark = async (caseId: string) => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/bookmarks/${caseId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })

      if (response.ok) {
        setBookmarks(prev => prev.filter(b => b.case_id !== caseId))
      }
    } catch (err) {
      console.error('Failed to delete bookmark:', err)
    }
  }

  // Copy share link
  const copyShareLink = (collectionId: string) => {
    const url = `${window.location.origin}/shared/${collectionId}`
    navigator.clipboard.writeText(url)
    setCopiedId(collectionId)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // Toggle collection public status
  const togglePublic = async (collection: Collection) => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections/${collection.id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ is_public: !collection.is_public })
      })

      if (response.ok) {
        setCollections(prev => prev.map(c =>
          c.id === collection.id ? { ...c, is_public: !c.is_public } : c
        ))
        if (selectedCollection?.id === collection.id) {
          setSelectedCollection({ ...selectedCollection, is_public: !selectedCollection.is_public })
        }
      }
    } catch (err) {
      console.error('Failed to update collection:', err)
    }
  }

  // Initial data fetch
  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        // Not logged in - stop loading (we'll show login prompt)
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      Promise.all([fetchCollections(), fetchBookmarks()]).finally(() => {
        setIsLoading(false)
      })
    }
  }, [user, authLoading, session])

  // If not configured or no user - show login prompt (don't wait for auth to finish)
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
        {/* Header */}
        <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
          <div className="container mx-auto px-4 py-3">
            <div className="flex items-center justify-between">
              <Link href="/" className="flex items-center space-x-3">
                <Scale className="h-8 w-8 text-neutral-700" />
                <div>
                  <h1 className="text-2xl font-bold text-neutral-900">Sage's Study Group</h1>
                  <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
                </div>
              </Link>
            </div>
          </div>
        </header>

        <div className="flex items-center justify-center py-32">
          <div className="text-center">
            <Bookmark className="h-16 w-16 text-neutral-300 mx-auto mb-6" />
            <h2 className="text-2xl font-bold text-neutral-900 mb-2">My Library</h2>
            <p className="text-neutral-600 mb-6">Sign in to save cases and create collections.</p>
            <Link
              href="/login"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
            >
              Sign in to continue
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Loading data (only when we have a user)
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-400" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Sage's Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
              </div>
            </Link>
            <nav className="flex items-center gap-4">
              <Link href="/" className="text-neutral-600 hover:text-neutral-900 transition">
                Search
              </Link>
              <Link href="/transparency" className="text-neutral-600 hover:text-neutral-900 transition">
                Transparency
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Page Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold text-neutral-900">My Library</h2>
              <p className="text-neutral-600 mt-1">Organize and save your cases</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-neutral-200 mb-6">
            <button
              onClick={() => {
                setActiveTab('collections')
                setSelectedCollection(null)
              }}
              className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition ${
                activeTab === 'collections'
                  ? 'text-blue-600 border-blue-600'
                  : 'text-neutral-500 border-transparent hover:text-neutral-700'
              }`}
            >
              <FolderOpen className="h-4 w-4" />
              Collections
              {collections.length > 0 && (
                <span className="bg-neutral-100 text-neutral-600 text-xs px-2 py-0.5 rounded-full">
                  {collections.length}
                </span>
              )}
            </button>
            <button
              onClick={() => {
                setActiveTab('bookmarks')
                setSelectedCollection(null)
              }}
              className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition ${
                activeTab === 'bookmarks'
                  ? 'text-blue-600 border-blue-600'
                  : 'text-neutral-500 border-transparent hover:text-neutral-700'
              }`}
            >
              <Bookmark className="h-4 w-4" />
              Bookmarks
              {bookmarks.length > 0 && (
                <span className="bg-neutral-100 text-neutral-600 text-xs px-2 py-0.5 rounded-full">
                  {bookmarks.length}
                </span>
              )}
            </button>
          </div>

          {/* Content */}
          <div className="flex gap-6">
            {/* Collections Tab */}
            {activeTab === 'collections' && (
              <>
                {/* Collections List */}
                <div className={`${selectedCollection ? 'w-1/3' : 'w-full'} space-y-4 transition-all`}>
                  {/* Create Collection Button */}
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-neutral-300 rounded-lg text-neutral-600 hover:border-blue-400 hover:text-blue-600 transition"
                  >
                    <Plus className="h-5 w-5" />
                    Create New Collection
                  </button>

                  {/* Collections */}
                  {collections.length === 0 ? (
                    <div className="text-center py-12 text-neutral-500">
                      <FolderOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No collections yet</p>
                      <p className="text-sm">Create a collection to organize your cases</p>
                    </div>
                  ) : (
                    collections.map(collection => (
                      <div
                        key={collection.id}
                        className={`bg-white rounded-lg border p-4 cursor-pointer transition ${
                          selectedCollection?.id === collection.id
                            ? 'border-blue-500 ring-2 ring-blue-100'
                            : 'border-neutral-200 hover:border-neutral-300'
                        }`}
                        onClick={() => fetchCollectionDetails(collection.id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-neutral-900 truncate">{collection.name}</h3>
                            {collection.description && (
                              <p className="text-sm text-neutral-500 mt-1 line-clamp-2">{collection.description}</p>
                            )}
                            <div className="flex items-center gap-3 mt-2">
                              {collection.subject && (
                                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                                  {collection.subject}
                                </span>
                              )}
                              <span className="text-xs text-neutral-500">
                                {collection.case_count} {collection.case_count === 1 ? 'case' : 'cases'}
                              </span>
                              {collection.is_public && (
                                <span className="text-xs text-green-600 flex items-center gap-1">
                                  <Share2 className="h-3 w-3" /> Public
                                </span>
                              )}
                            </div>
                          </div>
                          <ChevronRight className="h-5 w-5 text-neutral-400 flex-shrink-0 ml-2" />
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Collection Detail */}
                {selectedCollection && (
                  <div className="flex-1 bg-white rounded-lg border border-neutral-200 p-6">
                    <div className="flex items-start justify-between mb-6">
                      <div>
                        <h3 className="text-xl font-bold text-neutral-900">{selectedCollection.name}</h3>
                        {selectedCollection.description && (
                          <p className="text-neutral-600 mt-1">{selectedCollection.description}</p>
                        )}
                        {selectedCollection.subject && (
                          <span className="inline-block mt-2 text-sm bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                            {selectedCollection.subject}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Share Toggle */}
                        <button
                          onClick={() => togglePublic(selectedCollection)}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition ${
                            selectedCollection.is_public
                              ? 'bg-green-100 text-green-700 hover:bg-green-200'
                              : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'
                          }`}
                        >
                          <Share2 className="h-4 w-4" />
                          {selectedCollection.is_public ? 'Public' : 'Private'}
                        </button>

                        {/* Copy Link (if public) */}
                        {selectedCollection.is_public && (
                          <button
                            onClick={() => copyShareLink(selectedCollection.id)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200 transition"
                          >
                            {copiedId === selectedCollection.id ? (
                              <>
                                <Check className="h-4 w-4" />
                                Copied!
                              </>
                            ) : (
                              <>
                                <Copy className="h-4 w-4" />
                                Copy Link
                              </>
                            )}
                          </button>
                        )}

                        {/* Delete */}
                        <button
                          onClick={() => deleteCollection(selectedCollection.id)}
                          className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition"
                          title="Delete collection"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {/* Cases in Collection */}
                    {selectedCollection.cases.length === 0 ? (
                      <div className="text-center py-12 text-neutral-500">
                        <p>No cases in this collection yet</p>
                        <p className="text-sm mt-1">Search for cases and add them to this collection</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {selectedCollection.cases.map(c => (
                          <div
                            key={c.collection_case_id}
                            className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition"
                          >
                            <Link
                              href={`/case/${c.id}`}
                              className="flex-1 min-w-0"
                            >
                              <h4 className="font-medium text-neutral-900 hover:text-blue-600 truncate">
                                {c.title}
                              </h4>
                              <p className="text-sm text-neutral-500">
                                {c.court_name}{c.decision_date && ` (${new Date(c.decision_date).getFullYear()})`}
                              </p>
                              {c.notes && (
                                <p className="text-sm text-neutral-600 mt-1 italic">{c.notes}</p>
                              )}
                            </Link>
                            <button
                              onClick={(e) => {
                                e.preventDefault()
                                removeCaseFromCollection(selectedCollection.id, c.id)
                              }}
                              className="p-2 text-neutral-400 hover:text-red-500 transition"
                              title="Remove from collection"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Bookmarks Tab */}
            {activeTab === 'bookmarks' && (
              <div className="w-full">
                {bookmarks.length === 0 ? (
                  <div className="text-center py-12 text-neutral-500">
                    <Bookmark className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No bookmarks yet</p>
                    <p className="text-sm">Click the bookmark icon on any case to save it here</p>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {bookmarks.map(bookmark => (
                      <div
                        key={bookmark.id}
                        className="bg-white rounded-lg border border-neutral-200 p-4 hover:border-neutral-300 transition"
                      >
                        <div className="flex items-start justify-between">
                          <Link
                            href={`/case/${bookmark.case_id}`}
                            className="flex-1 min-w-0"
                          >
                            <h4 className="font-medium text-neutral-900 hover:text-blue-600 line-clamp-2">
                              {bookmark.title}
                            </h4>
                            <p className="text-sm text-neutral-500 mt-1">
                              {bookmark.court_name}{bookmark.decision_date && ` (${new Date(bookmark.decision_date).getFullYear()})`}
                            </p>
                            {bookmark.reporter_cite && (
                              <p className="text-xs text-neutral-400 mt-1">{bookmark.reporter_cite}</p>
                            )}
                          </Link>
                          <button
                            onClick={() => deleteBookmark(bookmark.case_id)}
                            className="p-1 text-neutral-400 hover:text-red-500 transition flex-shrink-0 ml-2"
                            title="Remove bookmark"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        {bookmark.notes && (
                          <p className="text-sm text-neutral-600 mt-2 pt-2 border-t border-neutral-100 italic">
                            {bookmark.notes}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Create Collection Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-xl font-bold text-neutral-900 mb-4">Create Collection</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  placeholder="e.g., Torts Cases"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Description
                </label>
                <textarea
                  value={newCollectionDescription}
                  onChange={(e) => setNewCollectionDescription(e.target.value)}
                  placeholder="Optional description..."
                  rows={2}
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Subject Tag
                </label>
                <input
                  type="text"
                  value={newCollectionSubject}
                  onChange={(e) => setNewCollectionSubject(e.target.value)}
                  placeholder="e.g., Torts, Contracts, Con Law"
                  className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_public"
                  checked={newCollectionPublic}
                  onChange={(e) => setNewCollectionPublic(e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded border-neutral-300 focus:ring-blue-500"
                />
                <label htmlFor="is_public" className="text-sm text-neutral-700">
                  Make this collection public (shareable link)
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-neutral-600 hover:text-neutral-800 transition"
              >
                Cancel
              </button>
              <button
                onClick={createCollection}
                disabled={!newCollectionName.trim() || isCreating}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Collection'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
