'use client'

import { useState, useEffect, useMemo, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import {
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
  Pencil,
} from 'lucide-react'
import Header from '@/components/Header'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensors,
  useSensor,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import SortableCollectionItem from '@/components/SortableCollectionItem'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Collection {
  id: string
  name: string
  description: string | null
  subject: string | null
  is_public: boolean
  case_count: number
  legal_text_count: number
  item_count: number
  created_at: string | null
}

interface CollectionDetail extends Collection {
  cases: CollectionCase[]
  legal_texts: CollectionLegalText[]
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
  position: number
}

interface CollectionLegalText {
  collection_lt_id: string
  item_id: number
  document_id: string
  slug: string
  title: string
  citation: string | null
  number: string | null
  notes: string | null
  added_at: string | null
  position: number
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
  return (
    <Suspense>
      <LibraryPageContent />
    </Suspense>
  )
}

function LibraryPageContent() {
  const { user, session, isLoading: authLoading, isConfigured } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [mounted, setMounted] = useState(false)

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

  // Note editing state
  const [editingNote, setEditingNote] = useState<{ itemKey: string; value: string } | null>(null)

  // DnD sensors
  const pointerSensor = useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  const keyboardSensor = useSensor(KeyboardSensor)
  const sensors = useSensors(pointerSensor, keyboardSensor)

  // Unified items sorted by position
  const unifiedItems = useMemo(() => {
    if (!selectedCollection) return []
    return [
      ...selectedCollection.cases.map(c => ({
        type: 'case' as const,
        key: `case-${c.id}`,
        sortId: `case-${c.id}`,
        position: c.position ?? 0,
        added_at: c.added_at,
        data: c
      })),
      ...(selectedCollection.legal_texts || []).map(lt => ({
        type: 'legal_text' as const,
        key: `lt-${lt.item_id}`,
        sortId: `lt-${lt.item_id}`,
        position: lt.position ?? 0,
        added_at: lt.added_at,
        data: lt
      }))
    ].sort((a, b) => {
      if (a.position !== b.position) return a.position - b.position
      if (!a.added_at) return 1
      if (!b.added_at) return -1
      return new Date(b.added_at).getTime() - new Date(a.added_at).getTime()
    })
  }, [selectedCollection])

  // Reorder API call
  const reorderItems = async (collectionId: string, items: { type: string; id: string }[]) => {
    if (!session?.access_token) return
    try {
      await fetch(`${API_URL}/api/v1/library/collections/${collectionId}/reorder`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ items })
      })
    } catch (err) {
      console.error('Failed to reorder items:', err)
    }
  }

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id || !selectedCollection) return

    const oldIndex = unifiedItems.findIndex(item => item.sortId === active.id)
    const newIndex = unifiedItems.findIndex(item => item.sortId === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const reordered = arrayMove(unifiedItems, oldIndex, newIndex)

    // Optimistically update state
    const updatedCases = selectedCollection.cases.map(c => {
      const idx = reordered.findIndex(r => r.type === 'case' && (r.data as CollectionCase).id === c.id)
      return { ...c, position: idx >= 0 ? idx : c.position }
    })
    const updatedLegalTexts = (selectedCollection.legal_texts || []).map(lt => {
      const idx = reordered.findIndex(r => r.type === 'legal_text' && (r.data as CollectionLegalText).item_id === lt.item_id)
      return { ...lt, position: idx >= 0 ? idx : lt.position }
    })

    setSelectedCollection({
      ...selectedCollection,
      cases: updatedCases,
      legal_texts: updatedLegalTexts
    })

    // Fire API call
    const apiItems = reordered.map(item => ({
      type: item.type,
      id: item.type === 'case'
        ? (item.data as CollectionCase).id
        : String((item.data as CollectionLegalText).item_id)
    }))
    reorderItems(selectedCollection.id, apiItems)
  }

  // Get auth headers
  const getAuthHeaders = (): Record<string, string> => {
    if (!session?.access_token) return {}
    return {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json'
    }
  }

  // Fetch collections
  const fetchCollections = async (token?: string) => {
    const accessToken = token || session?.access_token
    if (!accessToken) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
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
  const fetchBookmarks = async (token?: string) => {
    const accessToken = token || session?.access_token
    if (!accessToken) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/bookmarks`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
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
          c.id === collectionId
            ? { ...c, case_count: c.case_count - 1, item_count: c.item_count - 1 }
            : c
        ))
      }
    } catch (err) {
      console.error('Failed to remove case:', err)
    }
  }

  // Remove legal text from collection
  const removeLegalTextFromCollection = async (collectionId: string, itemId: number) => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/library/collections/${collectionId}/legal-texts/${itemId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })

      if (response.ok && selectedCollection) {
        setSelectedCollection({
          ...selectedCollection,
          legal_texts: selectedCollection.legal_texts.filter(lt => lt.item_id !== itemId)
        })
        // Update count in list
        setCollections(prev => prev.map(c =>
          c.id === collectionId
            ? { ...c, legal_text_count: c.legal_text_count - 1, item_count: c.item_count - 1 }
            : c
        ))
      }
    } catch (err) {
      console.error('Failed to remove legal text:', err)
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

  // Save note for a collection item
  const saveNote = async (collectionId: string, itemType: 'case' | 'legal_text', itemId: string | number, note: string) => {
    if (!session?.access_token) return

    const trimmed = note.trim()
    try {
      if (itemType === 'case') {
        await fetch(`${API_URL}/api/v1/library/collections/${collectionId}/cases`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ case_id: itemId, notes: trimmed || null })
        })
        if (selectedCollection) {
          setSelectedCollection({
            ...selectedCollection,
            cases: selectedCollection.cases.map(c =>
              c.id === itemId ? { ...c, notes: trimmed || null } : c
            )
          })
        }
      } else {
        await fetch(`${API_URL}/api/v1/library/collections/${collectionId}/legal-texts`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ legal_text_item_id: itemId, notes: trimmed || null })
        })
        if (selectedCollection) {
          setSelectedCollection({
            ...selectedCollection,
            legal_texts: selectedCollection.legal_texts.map(lt =>
              lt.item_id === itemId ? { ...lt, notes: trimmed || null } : lt
            )
          })
        }
      }
    } catch (err) {
      console.error('Failed to save note:', err)
    }
    setEditingNote(null)
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

  // Track when component is mounted (client-side)
  useEffect(() => {
    setMounted(true)
  }, [])

  // Initial data fetch - runs when session becomes available
  useEffect(() => {
    // Wait for mount and auth to finish loading
    if (!mounted || authLoading) return

    // If no user/session, just stop loading spinner
    if (!user || !session?.access_token) {
      setIsLoading(false)
      return
    }

    // Fetch data
    const loadData = async () => {
      setIsLoading(true)
      try {
        await Promise.all([
          fetchCollections(session.access_token),
          fetchBookmarks(session.access_token)
        ])
      } finally {
        setIsLoading(false)
      }
    }

    loadData().then(() => {
      // Auto-open collection if linked from a case page
      const collectionId = searchParams.get('collection')
      if (collectionId) {
        fetchCollectionDetails(collectionId)
      }
    })
  }, [mounted, authLoading, user, session])

  // Show login prompt before mount or if no user
  // This ensures we don't show a spinner during SSR
  if (!mounted || !user) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />

        <div className="flex items-center justify-center py-32">
          <div className="text-center">
            <Bookmark className="h-16 w-16 text-stone-300 mx-auto mb-6" />
            <h2 className="text-2xl font-bold text-stone-900 mb-2">My Library</h2>
            <p className="text-stone-600 mb-6">Sign in to save cases and create collections.</p>
            <Link
              href="/login"
              className="inline-flex items-center px-6 py-3 bg-sage-700 text-white rounded-lg font-medium hover:bg-sage-600 transition"
            >
              Sign in to continue
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Loading data (only when we have a user and are mounted)
  if (isLoading) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-stone-400" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Page Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold text-stone-900">My Library</h2>
              <p className="text-stone-600 mt-1">Organize and save your cases</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-stone-200 mb-6">
            <button
              onClick={() => {
                setActiveTab('collections')
                setSelectedCollection(null)
              }}
              className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition ${
                activeTab === 'collections'
                  ? 'text-sage-600 border-sage-600'
                  : 'text-stone-500 border-transparent hover:text-stone-700'
              }`}
            >
              <FolderOpen className="h-4 w-4" />
              Collections
              {collections.length > 0 && (
                <span className="bg-stone-100 text-stone-600 text-xs px-2 py-0.5 rounded-full">
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
                  ? 'text-sage-600 border-sage-600'
                  : 'text-stone-500 border-transparent hover:text-stone-700'
              }`}
            >
              <Bookmark className="h-4 w-4" />
              Bookmarks
              {bookmarks.length > 0 && (
                <span className="bg-stone-100 text-stone-600 text-xs px-2 py-0.5 rounded-full">
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
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-stone-200 rounded-lg text-stone-600 hover:border-sage-300 hover:text-sage-600 transition"
                  >
                    <Plus className="h-5 w-5" />
                    Create New Collection
                  </button>

                  {/* Collections */}
                  {collections.length === 0 ? (
                    <div className="text-center py-12 text-stone-500">
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
                            ? 'border-sage-500 ring-2 ring-sage-100'
                            : 'border-stone-200 hover:border-stone-200'
                        }`}
                        onClick={() => fetchCollectionDetails(collection.id)}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold text-stone-900 truncate">{collection.name}</h3>
                            {collection.description && (
                              <p className="text-sm text-stone-500 mt-1 line-clamp-2">{collection.description}</p>
                            )}
                            <div className="flex items-center gap-3 mt-2">
                              {collection.subject && (
                                <span className="text-xs bg-sage-50 text-sage-700 px-2 py-0.5 rounded">
                                  {collection.subject}
                                </span>
                              )}
                              <span className="text-xs text-stone-500">
                                {collection.item_count} {collection.item_count === 1 ? 'item' : 'items'}
                              </span>
                              {collection.is_public && (
                                <span className="text-xs text-green-600 flex items-center gap-1">
                                  <Share2 className="h-3 w-3" /> Public
                                </span>
                              )}
                            </div>
                          </div>
                          <ChevronRight className="h-5 w-5 text-stone-400 flex-shrink-0 ml-2" />
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {/* Collection Detail */}
                {selectedCollection && (
                  <div className="flex-1 min-w-0 bg-white rounded-lg border border-stone-200 p-6 overflow-hidden">
                    <div className="flex items-start justify-between mb-6">
                      <div>
                        <h3 className="text-xl font-bold text-stone-900">{selectedCollection.name}</h3>
                        {selectedCollection.description && (
                          <p className="text-stone-600 mt-1">{selectedCollection.description}</p>
                        )}
                        {selectedCollection.subject && (
                          <span className="inline-block mt-2 text-sm bg-sage-50 text-sage-700 px-2 py-0.5 rounded">
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
                              : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                          }`}
                        >
                          <Share2 className="h-4 w-4" />
                          {selectedCollection.is_public ? 'Public' : 'Private'}
                        </button>

                        {/* Copy Link (if public) */}
                        {selectedCollection.is_public && (
                          <button
                            onClick={() => copyShareLink(selectedCollection.id)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-sage-50 text-sage-700 rounded-lg text-sm hover:bg-sage-100 transition"
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

                    {/* Items in Collection — unified list sorted by position */}
                    {selectedCollection.cases.length === 0 && (!selectedCollection.legal_texts || selectedCollection.legal_texts.length === 0) ? (
                      <div className="text-center py-12 text-stone-500">
                        <p>No items in this collection yet</p>
                        <p className="text-sm mt-1">Search for cases or visit legal texts to add them</p>
                      </div>
                    ) : (
                      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                        <SortableContext items={unifiedItems.map(i => i.sortId)} strategy={verticalListSortingStrategy}>
                          <div className="space-y-3">
                            {unifiedItems.map(item => {
                              if (item.type === 'case') {
                                const c = item.data as CollectionCase
                                const isEditing = editingNote?.itemKey === item.key
                                return (
                                  <SortableCollectionItem key={item.key} id={item.sortId}>
                                    <div className="p-3 bg-stone-50 rounded-lg hover:bg-stone-100 transition overflow-hidden">
                                      <div className="flex items-center justify-between">
                                        <Link
                                          href={`/case/${c.id}?collection=${selectedCollection.id}`}
                                          className="flex-1 min-w-0 overflow-hidden"
                                        >
                                          <div className="flex items-center gap-2">
                                            <span className="inline-block text-xs bg-sage-50 text-sage-700 px-1.5 py-0.5 rounded flex-shrink-0">
                                              Case
                                            </span>
                                            <h4 className="font-medium text-stone-900 hover:text-sage-600 truncate">
                                              {c.title}
                                            </h4>
                                          </div>
                                          <p className="text-sm text-stone-500 mt-0.5 truncate">
                                            {c.court_name}{c.decision_date && ` (${new Date(c.decision_date).getFullYear()})`}
                                          </p>
                                        </Link>
                                        <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                                          <button
                                            onClick={(e) => {
                                              e.preventDefault()
                                              setEditingNote(isEditing ? null : { itemKey: item.key, value: c.notes || '' })
                                            }}
                                            className={`p-2 transition ${isEditing ? 'text-sage-600' : 'text-stone-400 hover:text-sage-600'}`}
                                            title="Edit note"
                                          >
                                            <Pencil className="h-4 w-4" />
                                          </button>
                                          <button
                                            onClick={(e) => {
                                              e.preventDefault()
                                              removeCaseFromCollection(selectedCollection.id, c.id)
                                            }}
                                            className="p-2 text-stone-400 hover:text-red-500 transition"
                                            title="Remove from collection"
                                          >
                                            <X className="h-4 w-4" />
                                          </button>
                                        </div>
                                      </div>
                                      {!isEditing && c.notes && (
                                        <p className="text-sm text-stone-600 mt-1 italic break-words overflow-hidden">{c.notes}</p>
                                      )}
                                      {isEditing && (
                                        <div className="mt-2">
                                          <textarea
                                            autoFocus
                                            value={editingNote.value}
                                            onChange={(e) => setEditingNote({ ...editingNote, value: e.target.value })}
                                            onKeyDown={(e) => {
                                              if (e.key === 'Escape') setEditingNote(null)
                                              if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault()
                                                saveNote(selectedCollection.id, 'case', c.id, editingNote.value)
                                              }
                                            }}
                                            placeholder="Add a note..."
                                            rows={2}
                                            className="w-full px-3 py-2 text-sm border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage-200 resize-none"
                                          />
                                          <div className="flex justify-end gap-2 mt-1">
                                            <button
                                              onClick={() => setEditingNote(null)}
                                              className="px-3 py-1 text-xs text-stone-500 hover:text-stone-700 transition"
                                            >
                                              Cancel
                                            </button>
                                            <button
                                              onClick={() => saveNote(selectedCollection.id, 'case', c.id, editingNote.value)}
                                              className="px-3 py-1 text-xs bg-sage-700 text-white rounded hover:bg-sage-600 transition"
                                            >
                                              Save
                                            </button>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  </SortableCollectionItem>
                                )
                              } else {
                                const lt = item.data as CollectionLegalText
                                const route = lt.document_id === 'frcp' ? '/rules'
                                  : lt.document_id === 'constitution' ? '/constitution'
                                  : '/statutes'
                                const typeLabel = lt.document_id === 'frcp' ? 'FRCP'
                                  : lt.document_id === 'constitution' ? 'Constitution'
                                  : 'Statute'
                                const isEditing = editingNote?.itemKey === item.key
                                return (
                                  <SortableCollectionItem key={item.key} id={item.sortId}>
                                    <div className="p-3 bg-stone-50 rounded-lg hover:bg-stone-100 transition overflow-hidden">
                                      <div className="flex items-center justify-between">
                                        <Link
                                          href={`${route}/${lt.slug}`}
                                          className="flex-1 min-w-0 overflow-hidden"
                                        >
                                          <div className="flex items-center gap-2">
                                            <span className="inline-block text-xs bg-sage-50 text-sage-700 px-1.5 py-0.5 rounded flex-shrink-0">
                                              {typeLabel}
                                            </span>
                                            <h4 className="font-medium text-stone-900 hover:text-sage-600 truncate">
                                              {lt.number ? `${typeLabel} ${lt.number}` : lt.title}
                                              {lt.number && lt.title ? ` \u2014 ${lt.title}` : ''}
                                            </h4>
                                          </div>
                                          {lt.citation && (
                                            <p className="text-sm text-stone-500 mt-0.5 truncate">{lt.citation}</p>
                                          )}
                                        </Link>
                                        <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                                          <button
                                            onClick={(e) => {
                                              e.preventDefault()
                                              setEditingNote(isEditing ? null : { itemKey: item.key, value: lt.notes || '' })
                                            }}
                                            className={`p-2 transition ${isEditing ? 'text-sage-600' : 'text-stone-400 hover:text-sage-600'}`}
                                            title="Edit note"
                                          >
                                            <Pencil className="h-4 w-4" />
                                          </button>
                                          <button
                                            onClick={(e) => {
                                              e.preventDefault()
                                              removeLegalTextFromCollection(selectedCollection.id, lt.item_id)
                                            }}
                                            className="p-2 text-stone-400 hover:text-red-500 transition"
                                            title="Remove from collection"
                                          >
                                            <X className="h-4 w-4" />
                                          </button>
                                        </div>
                                      </div>
                                      {!isEditing && lt.notes && (
                                        <p className="text-sm text-stone-600 mt-1 italic break-words overflow-hidden">{lt.notes}</p>
                                      )}
                                      {isEditing && (
                                        <div className="mt-2">
                                          <textarea
                                            autoFocus
                                            value={editingNote.value}
                                            onChange={(e) => setEditingNote({ ...editingNote, value: e.target.value })}
                                            onKeyDown={(e) => {
                                              if (e.key === 'Escape') setEditingNote(null)
                                              if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault()
                                                saveNote(selectedCollection.id, 'legal_text', lt.item_id, editingNote.value)
                                              }
                                            }}
                                            placeholder="Add a note..."
                                            rows={2}
                                            className="w-full px-3 py-2 text-sm border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage-200 resize-none"
                                          />
                                          <div className="flex justify-end gap-2 mt-1">
                                            <button
                                              onClick={() => setEditingNote(null)}
                                              className="px-3 py-1 text-xs text-stone-500 hover:text-stone-700 transition"
                                            >
                                              Cancel
                                            </button>
                                            <button
                                              onClick={() => saveNote(selectedCollection.id, 'legal_text', lt.item_id, editingNote.value)}
                                              className="px-3 py-1 text-xs bg-sage-700 text-white rounded hover:bg-sage-600 transition"
                                            >
                                              Save
                                            </button>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  </SortableCollectionItem>
                                )
                              }
                            })}
                          </div>
                        </SortableContext>
                      </DndContext>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Bookmarks Tab */}
            {activeTab === 'bookmarks' && (
              <div className="w-full">
                {bookmarks.length === 0 ? (
                  <div className="text-center py-12 text-stone-500">
                    <Bookmark className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No bookmarks yet</p>
                    <p className="text-sm">Click the bookmark icon on any case to save it here</p>
                  </div>
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {bookmarks.map(bookmark => (
                      <div
                        key={bookmark.id}
                        className="bg-white rounded-lg border border-stone-200 p-4 hover:border-stone-200 transition"
                      >
                        <div className="flex items-start justify-between">
                          <Link
                            href={`/case/${bookmark.case_id}`}
                            className="flex-1 min-w-0"
                          >
                            <h4 className="font-medium text-stone-900 hover:text-sage-600 line-clamp-2">
                              {bookmark.title}
                            </h4>
                            <p className="text-sm text-stone-500 mt-1">
                              {bookmark.court_name}{bookmark.decision_date && ` (${new Date(bookmark.decision_date).getFullYear()})`}
                            </p>
                            {bookmark.reporter_cite && (
                              <p className="text-xs text-stone-400 mt-1">{bookmark.reporter_cite}</p>
                            )}
                          </Link>
                          <button
                            onClick={() => deleteBookmark(bookmark.case_id)}
                            className="p-1 text-stone-400 hover:text-red-500 transition flex-shrink-0 ml-2"
                            title="Remove bookmark"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                        {bookmark.notes && (
                          <p className="text-sm text-stone-600 mt-2 pt-2 border-t border-stone-100 italic">
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
            <h3 className="text-xl font-bold text-stone-900 mb-4">Create Collection</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  placeholder="e.g., Torts Cases"
                  className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage-200"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  Description
                </label>
                <textarea
                  value={newCollectionDescription}
                  onChange={(e) => setNewCollectionDescription(e.target.value)}
                  placeholder="Optional description..."
                  rows={2}
                  className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage-200"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">
                  Subject Tag
                </label>
                <input
                  type="text"
                  value={newCollectionSubject}
                  onChange={(e) => setNewCollectionSubject(e.target.value)}
                  placeholder="e.g., Torts, Contracts, Con Law"
                  className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sage-200"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_public"
                  checked={newCollectionPublic}
                  onChange={(e) => setNewCollectionPublic(e.target.checked)}
                  className="w-4 h-4 text-sage-600 rounded border-stone-200 focus:ring-sage-200"
                />
                <label htmlFor="is_public" className="text-sm text-stone-700">
                  Make this collection public (shareable link)
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-stone-600 hover:text-stone-800 transition"
              >
                Cancel
              </button>
              <button
                onClick={createCollection}
                disabled={!newCollectionName.trim() || isCreating}
                className="px-4 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
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
