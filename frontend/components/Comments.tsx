'use client'

import { useState, useEffect } from 'react'
import { MessageSquare, Send, Edit2, Trash2, X, Check, Loader2, ChevronUp, ChevronDown } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import Link from 'next/link'
import { FormattedMessage } from '@/components/FormattedMessage'

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
  vote_count: number
  user_vote: number | null
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
  const fetchComments = async () => {
    try {
      const headers: Record<string, string> = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      const response = await fetch(`${API_URL}/api/v1/cases/${caseId}/comments`, { headers })
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

  useEffect(() => {
    fetchComments()
  }, [caseId])

  // Re-fetch with auth when session becomes available (to get user_vote)
  useEffect(() => {
    if (session?.access_token && comments.length > 0) {
      fetchComments()
    }
  }, [session?.access_token])

  // Get auth headers
  const getAuthHeaders = () => ({
    'Authorization': `Bearer ${session?.access_token}`,
    'Content-Type': 'application/json'
  })

  // Vote on a comment
  const voteComment = async (commentId: number, voteType: number) => {
    if (!session?.access_token) return

    const comment = comments.find(c => c.id === commentId)
    if (!comment) return

    // Toggle off if clicking same vote
    const newVote = comment.user_vote === voteType ? 0 : voteType

    try {
      const response = await fetch(`${API_URL}/api/v1/comments/${commentId}/vote`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ vote_type: newVote })
      })

      if (response.ok) {
        const data = await response.json()
        setComments(comments.map(c =>
          c.id === commentId
            ? { ...c, vote_count: data.vote_count, user_vote: data.user_vote }
            : c
        ))
      }
    } catch (error) {
      console.error('Failed to vote on comment:', error)
    }
  }

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
        <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-2 mb-6">
        <MessageSquare className="h-5 w-5 text-stone-600" />
        <h3 className="text-lg font-semibold text-stone-900">
          Discussion ({comments.length})
        </h3>
      </div>

      {/* Comments list */}
      {comments.length > 0 ? (
        <div className="space-y-4 mb-6">
          {comments.map((comment) => {
            const isOwnComment = user && comment.user_id === user.id
            return (
              <div key={comment.id} className="flex gap-3">
                {/* Vote column */}
                <div className="flex flex-col items-center gap-0 flex-shrink-0 pt-1">
                  <button
                    onClick={() => voteComment(comment.id, 1)}
                    disabled={!session?.access_token || !!isOwnComment}
                    title={!session?.access_token ? 'Sign in to vote' : isOwnComment ? "Can't vote on your own comment" : comment.user_vote === 1 ? 'Remove upvote' : 'Upvote'}
                    className={`p-0.5 rounded transition-colors ${
                      comment.user_vote === 1
                        ? 'text-sage-600'
                        : 'text-stone-300 hover:text-sage-500'
                    } disabled:opacity-40 disabled:cursor-not-allowed`}
                  >
                    <ChevronUp className="h-5 w-5" />
                  </button>
                  <span className={`text-xs font-medium leading-none ${
                    comment.vote_count > 0 ? 'text-sage-600' : comment.vote_count < 0 ? 'text-red-500' : 'text-stone-400'
                  }`}>
                    {comment.vote_count}
                  </span>
                  <button
                    onClick={() => voteComment(comment.id, -1)}
                    disabled={!session?.access_token || !!isOwnComment}
                    title={!session?.access_token ? 'Sign in to vote' : isOwnComment ? "Can't vote on your own comment" : comment.user_vote === -1 ? 'Remove downvote' : 'Downvote'}
                    className={`p-0.5 rounded transition-colors ${
                      comment.user_vote === -1
                        ? 'text-red-500'
                        : 'text-stone-300 hover:text-red-400'
                    } disabled:opacity-40 disabled:cursor-not-allowed`}
                  >
                    <ChevronDown className="h-5 w-5" />
                  </button>
                </div>

                {/* Avatar */}
                {comment.user.avatar_url ? (
                  <img
                    src={comment.user.avatar_url}
                    alt={getDisplayName(comment)}
                    className="h-10 w-10 rounded-full object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="h-10 w-10 rounded-full bg-sage-700 text-white flex items-center justify-center text-sm font-medium flex-shrink-0">
                    {getInitials(comment)}
                  </div>
                )}

                {/* Comment content */}
                <div className="flex-1 min-w-0">
                  <div className="bg-stone-50 rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2 mb-1">
                      {comment.user.profile_username ? (
                        <Link
                          href={`/users/${comment.user.profile_username}`}
                          className="font-medium text-stone-900 hover:text-sage-600"
                        >
                          {getDisplayName(comment)}
                        </Link>
                      ) : (
                        <span className="font-medium text-stone-900">
                          {getDisplayName(comment)}
                        </span>
                      )}
                      <span className="text-xs text-stone-500">
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
                          className="w-full px-3 py-2 border border-stone-200 rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 resize-none"
                          rows={3}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => saveEdit(comment.id)}
                            className="flex items-center gap-1 px-3 py-1 text-sm bg-sage-700 text-white rounded-lg hover:bg-sage-600"
                          >
                            <Check className="h-4 w-4" />
                            Save
                          </button>
                          <button
                            onClick={cancelEditing}
                            className="flex items-center gap-1 px-3 py-1 text-sm text-stone-600 hover:text-stone-900"
                          >
                            <X className="h-4 w-4" />
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      // Display mode
                      <div className="text-stone-700 text-sm">
                        <FormattedMessage content={comment.content} />
                      </div>
                    )}
                  </div>

                  {/* Actions (only for own comments) */}
                  {user && comment.user_id === user.id && editingId !== comment.id && (
                    <div className="flex items-center gap-3 mt-1 ml-2">
                      <button
                        onClick={() => startEditing(comment)}
                        className="text-xs text-stone-500 hover:text-stone-700 flex items-center gap-1"
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
                            className="text-xs text-stone-500 hover:text-stone-700"
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(comment.id)}
                          className="text-xs text-stone-500 hover:text-red-600 flex items-center gap-1"
                        >
                          <Trash2 className="h-3 w-3" />
                          Delete
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-stone-500 text-center py-6 mb-6">
          No comments yet. Be the first to start the discussion!
        </p>
      )}

      {/* Comment input */}
      {user ? (
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="h-10 w-10 rounded-full bg-sage-700 text-white flex items-center justify-center text-sm font-medium flex-shrink-0">
            {user.email?.slice(0, 2).toUpperCase() || 'ME'}
          </div>
          <div className="flex-1">
            <textarea
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Add a comment..."
              className="w-full px-4 py-3 border border-stone-200 rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 resize-none"
              rows={2}
            />
            <div className="flex justify-end mt-2">
              <button
                type="submit"
                disabled={!newComment.trim() || isSubmitting}
                className="flex items-center gap-2 px-4 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 disabled:opacity-50 disabled:cursor-not-allowed"
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
        <div className="text-center py-4 bg-stone-50 rounded-lg">
          <p className="text-stone-600 mb-2">Sign in to join the discussion</p>
          <Link
            href="/login"
            className="inline-flex items-center px-4 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 text-sm font-medium"
          >
            Sign In
          </Link>
        </div>
      )}
    </div>
  )
}
