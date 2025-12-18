'use client'

import { useState, useEffect } from 'react'
import { MessageSquare, Send, Edit2, Trash2, X, Check, Loader2 } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface CommentUser {
  username: string | null
  display_name: string | null
  avatar_url: string | null
  profile_username: string | null  // For linking to profile
}

interface Comment {
  id: number
  case_id: string
  user_id: string
  content: string
  is_edited: boolean
  created_at: string
  updated_at: string
  user: CommentUser
}

interface CommentsProps {
  caseId: string
}

// Helper function for relative time
function getRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) {
    return 'just now'
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60)
  if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes === 1 ? '' : 's'} ago`
  }

  const diffInHours = Math.floor(diffInMinutes / 60)
  if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours === 1 ? '' : 's'} ago`
  }

  const diffInDays = Math.floor(diffInHours / 24)
  if (diffInDays < 7) {
    return `${diffInDays} day${diffInDays === 1 ? '' : 's'} ago`
  }

  const diffInWeeks = Math.floor(diffInDays / 7)
  if (diffInWeeks < 4) {
    return `${diffInWeeks} week${diffInWeeks === 1 ? '' : 's'} ago`
  }

  const diffInMonths = Math.floor(diffInDays / 30)
  if (diffInMonths < 12) {
    return `${diffInMonths} month${diffInMonths === 1 ? '' : 's'} ago`
  }

  const diffInYears = Math.floor(diffInDays / 365)
  return `${diffInYears} year${diffInYears === 1 ? '' : 's'} ago`
}

export default function Comments({ caseId }: CommentsProps) {
  const { user, session } = useAuth()
  const [comments, setComments] = useState<Comment[]>([])
  const [newComment, setNewComment] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editContent, setEditContent] = useState('')
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)

  // Fetch comments
  useEffect(() => {
    const fetchComments = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/comments`)
        if (response.ok) {
          const data = await response.json()
          setComments(data.comments)
        }
      } catch (error) {
        console.error('Failed to fetch comments:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchComments()
  }, [caseId])

  // Get auth headers
  const getAuthHeaders = () => ({
    'Authorization': `Bearer ${session?.access_token}`,
    'Content-Type': 'application/json'
  })

  // Submit new comment
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newComment.trim() || !session?.access_token) return

    setIsSubmitting(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/comments`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ content: newComment.trim() })
      })

      if (response.ok) {
        const comment = await response.json()
        setComments([...comments, comment])
        setNewComment('')
      }
    } catch (error) {
      console.error('Failed to post comment:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Start editing
  const startEditing = (comment: Comment) => {
    setEditingId(comment.id)
    setEditContent(comment.content)
  }

  // Cancel editing
  const cancelEditing = () => {
    setEditingId(null)
    setEditContent('')
  }

  // Save edit
  const saveEdit = async (commentId: number) => {
    if (!editContent.trim() || !session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/comments/${commentId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ content: editContent.trim() })
      })

      if (response.ok) {
        const updated = await response.json()
        setComments(comments.map(c => c.id === commentId ? updated : c))
        cancelEditing()
      }
    } catch (error) {
      console.error('Failed to update comment:', error)
    }
  }

  // Delete comment
  const deleteComment = async (commentId: number) => {
    if (!session?.access_token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/comments/${commentId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })

      if (response.ok) {
        setComments(comments.filter(c => c.id !== commentId))
        setDeleteConfirmId(null)
      }
    } catch (error) {
      console.error('Failed to delete comment:', error)
    }
  }

  // Get display name for comment
  const getDisplayName = (comment: Comment) => {
    return comment.user.display_name || comment.user.username || 'Law Student'
  }

  // Get initials for avatar
  const getInitials = (comment: Comment) => {
    const name = getDisplayName(comment)
    return name.slice(0, 2).toUpperCase()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-2 mb-6">
        <MessageSquare className="h-5 w-5 text-neutral-600" />
        <h3 className="text-lg font-semibold text-neutral-900">
          Discussion ({comments.length})
        </h3>
      </div>

      {/* Comments list */}
      {comments.length > 0 ? (
        <div className="space-y-4 mb-6">
          {comments.map((comment) => (
            <div key={comment.id} className="flex gap-3">
              {/* Avatar */}
              {comment.user.avatar_url ? (
                <img
                  src={comment.user.avatar_url}
                  alt={getDisplayName(comment)}
                  className="h-10 w-10 rounded-full object-cover flex-shrink-0"
                />
              ) : (
                <div className="h-10 w-10 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium flex-shrink-0">
                  {getInitials(comment)}
                </div>
              )}

              {/* Comment content */}
              <div className="flex-1 min-w-0">
                <div className="bg-neutral-50 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    {comment.user.profile_username ? (
                      <Link
                        href={`/users/${comment.user.profile_username}`}
                        className="font-medium text-neutral-900 hover:text-blue-600"
                      >
                        {getDisplayName(comment)}
                      </Link>
                    ) : (
                      <span className="font-medium text-neutral-900">
                        {getDisplayName(comment)}
                      </span>
                    )}
                    <span className="text-xs text-neutral-500">
                      {getRelativeTime(comment.created_at)}
                      {comment.is_edited && ' (edited)'}
                    </span>
                  </div>

                  {editingId === comment.id ? (
                    // Edit mode
                    <div className="space-y-2">
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                        rows={3}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => saveEdit(comment.id)}
                          className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                        >
                          <Check className="h-4 w-4" />
                          Save
                        </button>
                        <button
                          onClick={cancelEditing}
                          className="flex items-center gap-1 px-3 py-1 text-sm text-neutral-600 hover:text-neutral-900"
                        >
                          <X className="h-4 w-4" />
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    // Display mode
                    <p className="text-neutral-700 whitespace-pre-wrap">
                      {comment.content}
                    </p>
                  )}
                </div>

                {/* Actions (only for own comments) */}
                {user && comment.user_id === user.id && editingId !== comment.id && (
                  <div className="flex items-center gap-3 mt-1 ml-2">
                    <button
                      onClick={() => startEditing(comment)}
                      className="text-xs text-neutral-500 hover:text-neutral-700 flex items-center gap-1"
                    >
                      <Edit2 className="h-3 w-3" />
                      Edit
                    </button>

                    {deleteConfirmId === comment.id ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-red-600">Delete?</span>
                        <button
                          onClick={() => deleteComment(comment.id)}
                          className="text-xs text-red-600 hover:text-red-700 font-medium"
                        >
                          Yes
                        </button>
                        <button
                          onClick={() => setDeleteConfirmId(null)}
                          className="text-xs text-neutral-500 hover:text-neutral-700"
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setDeleteConfirmId(comment.id)}
                        className="text-xs text-neutral-500 hover:text-red-600 flex items-center gap-1"
                      >
                        <Trash2 className="h-3 w-3" />
                        Delete
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-neutral-500 text-center py-6 mb-6">
          No comments yet. Be the first to start the discussion!
        </p>
      )}

      {/* Comment input */}
      {user ? (
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="h-10 w-10 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-medium flex-shrink-0">
            {user.email?.slice(0, 2).toUpperCase() || 'ME'}
          </div>
          <div className="flex-1">
            <textarea
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Add a comment..."
              className="w-full px-4 py-3 border border-neutral-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              rows={2}
            />
            <div className="flex justify-end mt-2">
              <button
                type="submit"
                disabled={!newComment.trim() || isSubmitting}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Post
              </button>
            </div>
          </div>
        </form>
      ) : (
        <div className="text-center py-4 bg-neutral-50 rounded-lg">
          <p className="text-neutral-600 mb-2">Sign in to join the discussion</p>
          <Link
            href="/login"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            Sign In
          </Link>
        </div>
      )}
    </div>
  )
}
