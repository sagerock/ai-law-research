'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { FolderPlus, ChevronDown, Check, Loader2 } from 'lucide-react'
import { API_URL } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

interface UserCollection {
  id: string
  name: string
  subject: string | null
}

interface AddToCollectionDropdownProps {
  itemType: 'case' | 'legal_text'
  itemId: string
}

export default function AddToCollectionDropdown({ itemType, itemId }: AddToCollectionDropdownProps) {
  const router = useRouter()
  const { user, session } = useAuth()
  const [collections, setCollections] = useState<UserCollection[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [addingTo, setAddingTo] = useState<string | null>(null)
  const [itemInCollections, setItemInCollections] = useState<Set<string>>(new Set())
  const dropdownRef = useRef<HTMLDivElement>(null)

  const getAuthHeaders = (): Record<string, string> => {
    if (!session?.access_token) return {}
    return {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json'
    }
  }

  // Fetch collections and check membership
  useEffect(() => {
    if (!user || !session?.access_token) return

    const fetchCollections = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/library/collections`, {
          headers: getAuthHeaders()
        })
        if (!response.ok) return
        const data = await response.json()
        setCollections(data.collections)

        // Check which collections contain this item
        const inCollections = new Set<string>()
        for (const collection of data.collections) {
          const detailResponse = await fetch(`${API_URL}/api/v1/library/collections/${collection.id}`, {
            headers: getAuthHeaders()
          })
          if (detailResponse.ok) {
            const detail = await detailResponse.json()
            if (itemType === 'case') {
              if (detail.cases.some((c: { id: string }) => c.id === itemId)) {
                inCollections.add(collection.id)
              }
            } else {
              if (detail.legal_texts?.some((lt: { item_id: number }) => String(lt.item_id) === itemId)) {
                inCollections.add(collection.id)
              }
            }
          }
        }
        setItemInCollections(inCollections)
      } catch (err) {
        console.log('Failed to fetch collections:', err)
      }
    }

    fetchCollections()
  }, [user, session, itemId, itemType])

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggleCollection = async (collectionId: string) => {
    if (!user || !session?.access_token) return

    setAddingTo(collectionId)
    try {
      if (itemInCollections.has(collectionId)) {
        // Remove
        const endpoint = itemType === 'case'
          ? `${API_URL}/api/v1/library/collections/${collectionId}/cases/${itemId}`
          : `${API_URL}/api/v1/library/collections/${collectionId}/legal-texts/${itemId}`
        const response = await fetch(endpoint, {
          method: 'DELETE',
          headers: getAuthHeaders()
        })
        if (response.ok) {
          setItemInCollections(prev => {
            const next = new Set(prev)
            next.delete(collectionId)
            return next
          })
        }
      } else {
        // Add
        const endpoint = itemType === 'case'
          ? `${API_URL}/api/v1/library/collections/${collectionId}/cases`
          : `${API_URL}/api/v1/library/collections/${collectionId}/legal-texts`
        const body = itemType === 'case'
          ? { case_id: itemId }
          : { legal_text_item_id: parseInt(itemId) }
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(body)
        })
        if (response.ok) {
          setItemInCollections(prev => new Set(prev).add(collectionId))
        }
      }
    } catch (err) {
      console.error('Failed to toggle collection:', err)
    } finally {
      setAddingTo(null)
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => {
          if (!user) {
            router.push('/login')
            return
          }
          setShowDropdown(!showDropdown)
        }}
        className="flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-700 transition-colors"
        title="Add to collection"
      >
        <FolderPlus className="h-4 w-4" />
        <span className="hidden sm:inline">Collection</span>
        <ChevronDown className={`h-3 w-3 transition ${showDropdown ? 'rotate-180' : ''}`} />
      </button>

      {showDropdown && (
        <div className="absolute top-full right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-stone-200 py-2 z-50">
          {collections.length === 0 ? (
            <div className="px-4 py-3 text-sm text-stone-500">
              <p>No collections yet</p>
              <Link
                href="/library"
                className="text-sage-600 hover:text-sage-700 font-medium"
                onClick={() => setShowDropdown(false)}
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
                  disabled={addingTo === collection.id}
                  className="w-full flex items-center justify-between px-4 py-2 hover:bg-stone-50 text-left"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-stone-900 truncate">{collection.name}</p>
                    {collection.subject && (
                      <p className="text-xs text-stone-500">{collection.subject}</p>
                    )}
                  </div>
                  {addingTo === collection.id ? (
                    <Loader2 className="h-4 w-4 animate-spin text-stone-400 flex-shrink-0" />
                  ) : itemInCollections.has(collection.id) ? (
                    <Check className="h-4 w-4 text-green-600 flex-shrink-0" />
                  ) : null}
                </button>
              ))}
              <div className="border-t mt-2 pt-2">
                <Link
                  href="/library"
                  className="flex items-center px-4 py-2 text-sm text-sage-600 hover:bg-sage-50"
                  onClick={() => setShowDropdown(false)}
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
  )
}
