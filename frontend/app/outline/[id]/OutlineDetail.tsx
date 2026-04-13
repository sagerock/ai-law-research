'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import { Outline, OutlineConversation, OutlineMessage } from '@/types'
import Markdown from 'react-markdown'
import Header from '@/components/Header'
import {
  FileText,
  Download,
  GitFork,
  Edit3,
  Trash2,
  Loader2,
  Send,
  BookOpen,
  PenTool,
  ArrowLeft,
  MessageSquare,
  AlignLeft,
  Shuffle,
  MessageCircle,
  ChevronDown,
  X,
  Check,
} from 'lucide-react'

interface OutlineDetailProps {
  outlineId: string
}

export default function OutlineDetail({ outlineId }: OutlineDetailProps) {
  const router = useRouter()
  const { user, session } = useAuth()

  // Outline data
  const [outline, setOutline] = useState<Outline | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Edit mode
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editVisibility, setEditVisibility] = useState<'private' | 'unlisted' | 'public'>('private')
  const [editShowAuthor, setEditShowAuthor] = useState(false)
  const [editShowSchool, setEditShowSchool] = useState(false)
  const [editDescription, setEditDescription] = useState('')
  const [saving, setSaving] = useState(false)

  // Study session
  const [activeMode, setActiveMode] = useState<'multiple_choice' | 'short_answer' | 'practice_essay' | 'ask' | null>(null)
  const [pendingMode, setPendingMode] = useState<'multiple_choice' | 'short_answer' | 'practice_essay' | 'ask' | null>(null)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<OutlineMessage[]>([])
  const [input, setInput] = useState('')
  const [askInput, setAskInput] = useState('')
  const [sending, setSending] = useState(false)
  const [startingStudy, setStartingStudy] = useState(false)

  // Topic selection
  const [topics, setTopics] = useState<string[]>([])
  const [loadingTopics, setLoadingTopics] = useState(false)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [customTopic, setCustomTopic] = useState('')

  // Past sessions
  const [pastSessions, setPastSessions] = useState<OutlineConversation[]>([])

  // Fork state
  const [forking, setForking] = useState(false)

  // Delete confirmation
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const chatEndRef = useRef<HTMLDivElement>(null)

  const getHeaders = useCallback((): Record<string, string> => {
    if (!session?.access_token) return {}
    return { 'Authorization': `Bearer ${session.access_token}`, 'Content-Type': 'application/json' }
  }, [session?.access_token])

  // Fetch outline
  useEffect(() => {
    const fetchOutline = async () => {
      setLoading(true)
      setError(null)
      try {
        const headers: Record<string, string> = session?.access_token
          ? { 'Authorization': `Bearer ${session.access_token}` }
          : {}
        const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}`, { headers })
        if (!res.ok) {
          if (res.status === 404) setError('Outline not found.')
          else setError('Failed to load outline.')
          return
        }
        const data = await res.json()
        setOutline(data)
        setEditTitle(data.title)
        setEditVisibility(data.visibility)
        setEditDescription(data.description || '')
        setEditShowAuthor(data.show_author || false)
        setEditShowSchool(data.show_school || false)
      } catch {
        setError('Failed to load outline.')
      } finally {
        setLoading(false)
      }
    }

    fetchOutline()
  }, [outlineId, session?.access_token])

  // Fetch past sessions
  useEffect(() => {
    if (!session?.access_token) return
    const fetchSessions = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/conversations`, {
          headers: { 'Authorization': `Bearer ${session.access_token}` },
        })
        if (res.ok) {
          const data = await res.json()
          setPastSessions(data.conversations || [])
        }
      } catch {
        // silently ignore
      }
    }
    fetchSessions()
  }, [outlineId, session?.access_token])

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSaveEdit = async () => {
    if (!outline) return
    setSaving(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outline.id}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({
          title: editTitle.trim(),
          visibility: editVisibility,
          description: editDescription.trim() || null,
          show_author: editShowAuthor,
          show_school: editShowSchool,
        }),
      })
      if (!res.ok) throw new Error('Save failed')
      const updated = await res.json()
      setOutline(updated)
      setEditing(false)
    } catch {
      // Could show an error toast here
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!outline) return
    setDeleting(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outline.id}`, {
        method: 'DELETE',
        headers: getHeaders(),
      })
      if (!res.ok) throw new Error('Delete failed')
      router.push('/outlines')
    } catch {
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  const handleFork = async () => {
    if (!outline || !session?.access_token) return
    setForking(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outline.id}/fork`, {
        method: 'POST',
        headers: getHeaders(),
      })
      if (!res.ok) throw new Error('Fork failed')
      const forked = await res.json()
      router.push(`/outline/${forked.id}`)
    } catch {
      setForking(false)
    }
  }

  const selectMode = async (mode: 'multiple_choice' | 'short_answer' | 'practice_essay' | 'ask') => {
    setPendingMode(mode)
    setSelectedTopic(null)
    setCustomTopic('')
    // Fetch topics if not already loaded
    if (topics.length === 0 && !loadingTopics && session?.access_token) {
      setLoadingTopics(true)
      try {
        // Try cached topics first
        const cached = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/topics`, {
          headers: { 'Authorization': `Bearer ${session.access_token}` },
        })
        if (cached.ok) {
          const data = await cached.json()
          if (data.topics && data.topics.length > 0) {
            setTopics(data.topics)
            setLoadingTopics(false)
            return
          }
        }
        // Extract topics
        const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/extract-topics`, {
          method: 'POST',
          headers: getHeaders(),
        })
        if (res.ok) {
          const data = await res.json()
          setTopics(data.topics || [])
        }
      } catch { /* ignore */ } finally {
        setLoadingTopics(false)
      }
    }
  }

  const askQuestion = async () => {
    if (!session?.access_token || !outline || !askInput.trim()) return
    setStartingStudy(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outline.id}/study`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ mode: 'ask', topic: askInput.trim() }),
      })
      if (!res.ok) throw new Error('Failed to start')
      const data = await res.json()
      setConversationId(data.conversation_id)
      setActiveMode('ask')
      setMessages(data.messages || [])
      setAskInput('')
    } catch { /* ignore */ } finally {
      setStartingStudy(false)
    }
  }

  const startStudy = async (topic?: string | null) => {
    if (!session?.access_token || !outline || !pendingMode) return
    setStartingStudy(true)
    try {
      const body: { mode: string; topic?: string } = { mode: pendingMode }
      if (topic) body.topic = topic
      const res = await fetch(`${API_URL}/api/v1/outlines/${outline.id}/study`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error('Failed to start session')
      const data = await res.json()
      setConversationId(data.conversation_id)
      setActiveMode(pendingMode)
      setPendingMode(null)
      setMessages(data.messages || [])
      // Refresh past sessions list
      const sessRes = await fetch(`${API_URL}/api/v1/outlines/${outlineId}/conversations`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` },
      })
      if (sessRes.ok) {
        const sessData = await sessRes.json()
        setPastSessions(sessData.conversations || [])
      }
    } catch {
      // silently ignore
    } finally {
      setStartingStudy(false)
    }
  }

  const loadPastSession = async (convId: number) => {
    if (!session?.access_token || !outline) return
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outline.id}/conversations/${convId}`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` },
      })
      if (!res.ok) return
      const data = await res.json()
      setConversationId(convId)
      setActiveMode(data.mode)
      setMessages(data.messages || [])
    } catch {
      // silently ignore
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || !conversationId || !outline || sending) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setSending(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/${outline.id}/conversations/${conversationId}/message`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ content: userMsg }),
      })
      if (!res.ok) throw new Error('Send failed')
      const data = await res.json()
      setMessages(prev => [...prev, { role: 'assistant', content: data.content }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }])
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && activeMode === 'multiple_choice') {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const modeName = (mode: string) =>
    mode === 'multiple_choice' ? 'Multiple Choice' : mode === 'short_answer' ? 'Short Answer' : mode === 'ask' ? 'Q&A' : 'Practice Essay'

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="flex items-center justify-center py-32">
          <Loader2 className="h-8 w-8 animate-spin text-stone-400" />
        </div>
      </div>
    )
  }

  // Error state
  if (error || !outline) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="container mx-auto px-4 py-16 max-w-3xl text-center">
          <FileText className="h-16 w-16 text-stone-300 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-stone-800 mb-2">{error || 'Outline not found'}</h2>
          <Link href="/study/outlines" className="mt-4 inline-flex items-center text-sage-700 hover:underline">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Outlines
          </Link>
        </div>
      </div>
    )
  }

  const isOwner = outline.is_owner || (user && outline.user_id === user.id)
  const hasContent = !!(outline.has_content || outline.content)
  const isLoggedIn = !!user

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Back link */}
        <div className="mb-6">
          <Link
            href="/study/outlines"
            className="inline-flex items-center text-stone-500 hover:text-stone-700 text-sm transition"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Outlines
          </Link>
        </div>

        {/* Outline header card */}
        <div className="bg-white rounded-xl border border-stone-200 p-6 mb-6">
          {editing ? (
            /* Edit mode */
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Title</label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none text-stone-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Description</label>
                <textarea
                  value={editDescription}
                  onChange={e => setEditDescription(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none resize-none text-stone-700"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700 mb-1">Visibility</label>
                <select
                  value={editVisibility}
                  onChange={e => setEditVisibility(e.target.value as 'private' | 'unlisted' | 'public')}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none bg-white"
                >
                  <option value="private">Private — only you can see it</option>
                  <option value="unlisted">Unlisted — anyone with the link</option>
                  <option value="public">Public — visible to everyone</option>
                </select>
              </div>
              {editVisibility !== 'private' && (
                <div className="space-y-2 p-3 bg-stone-50 rounded-lg">
                  <p className="text-xs font-medium text-stone-600 mb-2">What to show publicly:</p>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editShowAuthor}
                      onChange={(e) => setEditShowAuthor(e.target.checked)}
                      className="h-4 w-4 text-sage-600 rounded"
                    />
                    <span className="text-sm text-stone-700">Show my name</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editShowSchool}
                      onChange={(e) => setEditShowSchool(e.target.checked)}
                      className="h-4 w-4 text-sage-600 rounded"
                    />
                    <span className="text-sm text-stone-700">Show my law school</span>
                  </label>
                </div>
              )}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleSaveEdit}
                  disabled={saving || !editTitle.trim()}
                  className="inline-flex items-center px-4 py-2 bg-sage-700 text-white rounded-lg text-sm font-medium hover:bg-sage-600 disabled:bg-stone-300 disabled:cursor-not-allowed transition"
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Check className="h-4 w-4 mr-2" />}
                  Save Changes
                </button>
                <button
                  onClick={() => {
                    setEditing(false)
                    setEditTitle(outline.title)
                    setEditVisibility(outline.visibility)
                    setEditDescription(outline.description || '')
                  }}
                  className="inline-flex items-center px-4 py-2 text-stone-600 border rounded-lg text-sm font-medium hover:bg-stone-50 transition"
                >
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            /* View mode */
            <>
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="min-w-0 flex-1">
                  <h1 className="text-2xl font-bold text-stone-900 leading-tight">{outline.title}</h1>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    <span className="px-2.5 py-1 bg-sage-50 text-sage-700 text-xs font-medium rounded-full">
                      {outline.subject}
                    </span>
                    {outline.visibility === 'private' && (
                      <span className="px-2.5 py-1 bg-stone-100 text-stone-600 text-xs font-medium rounded-full">
                        Private
                      </span>
                    )}
                    {outline.visibility === 'unlisted' && (
                      <span className="px-2.5 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded-full">
                        Unlisted
                      </span>
                    )}
                    {outline.visibility === 'public' && (
                      <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                        Public
                      </span>
                    )}
                    {outline.fork_count > 0 && (
                      <span className="flex items-center text-xs text-stone-500">
                        <GitFork className="h-3.5 w-3.5 mr-1" />
                        {outline.fork_count} {outline.fork_count === 1 ? 'fork' : 'forks'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Owner controls */}
                {isOwner && (
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => setEditing(true)}
                      className="p-2 text-stone-500 hover:text-stone-700 hover:bg-stone-100 rounded-lg transition"
                      title="Edit outline"
                    >
                      <Edit3 className="h-4 w-4" />
                    </button>
                    {!confirmDelete ? (
                      <button
                        onClick={() => setConfirmDelete(true)}
                        className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
                        title="Delete outline"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    ) : (
                      <div className="flex items-center gap-2 bg-red-50 rounded-lg px-3 py-1.5">
                        <span className="text-xs text-red-700 font-medium">Delete?</span>
                        <button
                          onClick={handleDelete}
                          disabled={deleting}
                          className="text-xs text-red-700 font-bold hover:text-red-900 transition"
                        >
                          {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Yes'}
                        </button>
                        <button
                          onClick={() => setConfirmDelete(false)}
                          className="text-xs text-stone-500 hover:text-stone-700 transition"
                        >
                          No
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Description */}
              {outline.description && (
                <p className="text-stone-600 text-sm mb-4">{outline.description}</p>
              )}

              {/* Metadata */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-stone-500 mb-4">
                {outline.professor && <span>Prof. {outline.professor}</span>}
                {outline.law_school && <span>{outline.law_school}</span>}
                {outline.semester && <span>{outline.semester}</span>}
                {outline.year && <span>{outline.year}</span>}
                {!isOwner && (outline.username || outline.full_name) && (
                  <span>
                    by {outline.full_name || outline.username}
                    {outline.author_school ? ` · ${outline.author_school}` : ''}
                  </span>
                )}
                <span>{formatDate(outline.created_at)}</span>
                {outline.file_size && <span>{formatFileSize(outline.file_size)}</span>}
              </div>

              {/* Action buttons */}
              <div className="flex flex-wrap gap-3">
                <a
                  href={`${API_URL}/api/v1/outlines/${outline.id}/download`}
                  className="inline-flex items-center px-4 py-2 bg-sage-700 text-white rounded-lg text-sm font-medium hover:bg-sage-600 transition"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </a>
                {!isOwner && isLoggedIn && (
                  <button
                    onClick={handleFork}
                    disabled={forking}
                    className="inline-flex items-center px-4 py-2 border border-stone-200 text-stone-700 rounded-lg text-sm font-medium hover:bg-stone-50 transition disabled:opacity-50"
                  >
                    {forking ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <GitFork className="h-4 w-4 mr-2" />
                    )}
                    Fork to My Library
                  </button>
                )}
              </div>
            </>
          )}
        </div>

        {/* Content preview (collapsed by default) */}
        {outline.content && (
          <details className="bg-white rounded-xl border border-stone-200 mb-6 group">
            <summary className="flex items-center justify-between cursor-pointer p-4 hover:bg-stone-50 transition rounded-xl list-none">
              <div className="flex items-center text-sm font-medium text-stone-600">
                <FileText className="h-4 w-4 mr-2 text-stone-400" />
                Outline Content
                <span className="ml-2 text-stone-400 font-normal">({Math.round(outline.content.length / 1000)}k characters)</span>
              </div>
              <ChevronDown className="h-4 w-4 text-stone-400 transition-transform group-open:rotate-180" />
            </summary>
            <div className="px-4 pb-4">
              <pre className="text-sm text-stone-700 whitespace-pre-wrap font-mono leading-relaxed bg-stone-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                {outline.content.length > 5000
                  ? outline.content.slice(0, 5000) + '\n\n...[content truncated]'
                  : outline.content}
              </pre>
            </div>
          </details>
        )}

        {/* AI Study Tools */}
        {isLoggedIn && hasContent && (
          <div className="bg-white rounded-xl border border-stone-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-stone-900 mb-1 flex items-center">
              <MessageSquare className="h-5 w-5 mr-2 text-stone-500" />
              AI Study Tools
            </h2>
            <p className="text-sm text-stone-500 mb-5">Practice with AI using this outline as your study material.</p>

            {/* Ask a question box */}
            {!activeMode && !pendingMode && !startingStudy && (
              <div className="mb-6">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <MessageCircle className="absolute left-3 top-3 h-4 w-4 text-stone-400" />
                    <input
                      type="text"
                      value={askInput}
                      onChange={(e) => setAskInput(e.target.value)}
                      placeholder="Ask a question about your outline..."
                      className="w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && askInput.trim()) askQuestion()
                      }}
                    />
                  </div>
                  <button
                    onClick={askQuestion}
                    disabled={!askInput.trim()}
                    className="px-4 py-2.5 bg-sage-700 text-white rounded-lg text-sm font-medium hover:bg-sage-600 disabled:bg-stone-300 disabled:cursor-not-allowed transition"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-4 flex items-center gap-3">
                  <div className="flex-1 border-t border-stone-200" />
                  <span className="text-xs text-stone-400">or practice with</span>
                  <div className="flex-1 border-t border-stone-200" />
                </div>
              </div>
            )}

            {!activeMode ? (
              <>
                {startingStudy ? (
                  <div className="flex items-center justify-center py-10">
                    <Loader2 className="h-6 w-6 animate-spin text-stone-400 mr-3" />
                    <span className="text-stone-500">Starting session...</span>
                  </div>
                ) : !pendingMode ? (
                  /* Step 1: Pick a mode */
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                    <button
                      onClick={() => selectMode('multiple_choice')}
                      className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border-2 border-stone-200 hover:border-sage-300 hover:bg-sage-50 transition group"
                    >
                      <BookOpen className="h-10 w-10 text-stone-400 group-hover:text-sage-600 transition" />
                      <div className="text-center">
                        <div className="font-semibold text-stone-800 group-hover:text-sage-700 transition">Multiple Choice</div>
                        <div className="text-xs text-stone-500 mt-1">Pick from answer options</div>
                      </div>
                    </button>
                    <button
                      onClick={() => selectMode('short_answer')}
                      className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border-2 border-stone-200 hover:border-sage-300 hover:bg-sage-50 transition group"
                    >
                      <AlignLeft className="h-10 w-10 text-stone-400 group-hover:text-sage-600 transition" />
                      <div className="text-center">
                        <div className="font-semibold text-stone-800 group-hover:text-sage-700 transition">Short Answer</div>
                        <div className="text-xs text-stone-500 mt-1">Explain concepts in your own words</div>
                      </div>
                    </button>
                    <button
                      onClick={() => selectMode('practice_essay')}
                      className="flex flex-col items-center justify-center gap-3 p-6 rounded-xl border-2 border-stone-200 hover:border-sage-300 hover:bg-sage-50 transition group"
                    >
                      <PenTool className="h-10 w-10 text-stone-400 group-hover:text-sage-600 transition" />
                      <div className="text-center">
                        <div className="font-semibold text-stone-800 group-hover:text-sage-700 transition">Practice Essay</div>
                        <div className="text-xs text-stone-500 mt-1">Issue spotters with AI feedback</div>
                      </div>
                    </button>
                  </div>
                ) : (
                  /* Step 2: Pick a topic (or random) */
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-stone-800">
                        {pendingMode === 'multiple_choice' ? 'Multiple Choice' : pendingMode === 'short_answer' ? 'Short Answer' : 'Practice Essay'} — Pick a topic
                      </h3>
                      <button onClick={() => setPendingMode(null)} className="text-sm text-stone-500 hover:text-stone-700">
                        <ArrowLeft className="h-4 w-4 inline mr-1" />Back
                      </button>
                    </div>

                    {/* Random / all topics option */}
                    <button
                      onClick={() => startStudy(null)}
                      className="w-full flex items-center gap-3 p-3 mb-3 rounded-lg border-2 border-sage-200 bg-sage-50 hover:bg-sage-100 transition text-left"
                    >
                      <Shuffle className="h-5 w-5 text-sage-600" />
                      <div>
                        <div className="font-medium text-sage-800">Random topics</div>
                        <div className="text-xs text-sage-600">AI picks from anywhere in your outline</div>
                      </div>
                    </button>

                    {/* Topic suggestions */}
                    {loadingTopics ? (
                      <div className="flex items-center gap-2 py-4 text-sm text-stone-500">
                        <Loader2 className="h-4 w-4 animate-spin" /> Analyzing your outline for topics...
                      </div>
                    ) : topics.length > 0 ? (
                      <div className="mb-4">
                        <div className="text-sm text-stone-600 mb-2">Or focus on a specific topic:</div>
                        <div className="flex flex-wrap gap-2">
                          {topics.map(t => (
                            <button
                              key={t}
                              onClick={() => { setSelectedTopic(t); setCustomTopic('') }}
                              className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
                                selectedTopic === t
                                  ? 'bg-sage-700 text-white'
                                  : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
                              }`}
                            >
                              {t}
                            </button>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {/* Custom topic input */}
                    <div className="flex gap-2 mt-3">
                      <input
                        type="text"
                        value={customTopic}
                        onChange={(e) => { setCustomTopic(e.target.value); setSelectedTopic(null) }}
                        placeholder="Or type a topic..."
                        className="flex-1 px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && customTopic.trim()) {
                            startStudy(customTopic.trim())
                          }
                        }}
                      />
                      {(selectedTopic || customTopic.trim()) && (
                        <button
                          onClick={() => startStudy(selectedTopic || customTopic.trim())}
                          className="px-4 py-2 bg-sage-700 text-white rounded-lg text-sm font-medium hover:bg-sage-600 transition"
                        >
                          Start
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Past sessions */}
                {pastSessions.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium text-stone-700 mb-3">Past Sessions</h3>
                    <div className="space-y-2">
                      {pastSessions.map(sess => (
                        <button
                          key={sess.id}
                          onClick={() => loadPastSession(sess.id)}
                          className="w-full flex items-center justify-between px-4 py-3 rounded-lg bg-stone-50 hover:bg-stone-100 transition text-left"
                        >
                          <div className="flex items-center gap-3">
                            {sess.mode === 'multiple_choice' ? (
                              <BookOpen className="h-4 w-4 text-stone-400" />
                            ) : sess.mode === 'short_answer' ? (
                              <AlignLeft className="h-4 w-4 text-stone-400" />
                            ) : sess.mode === 'ask' ? (
                              <MessageCircle className="h-4 w-4 text-stone-400" />
                            ) : (
                              <PenTool className="h-4 w-4 text-stone-400" />
                            )}
                            <div>
                              <div className="text-sm font-medium text-stone-800">{modeName(sess.mode)}</div>
                              <div className="text-xs text-stone-500">
                                {sess.message_count} messages · {formatDate(sess.updated_at)}
                              </div>
                            </div>
                          </div>
                          <MessageSquare className="h-4 w-4 text-stone-300" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              /* Active chat session */
              <div>
                {/* Session header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    {activeMode === 'multiple_choice' ? (
                      <BookOpen className="h-5 w-5 text-sage-600" />
                    ) : activeMode === 'short_answer' ? (
                      <AlignLeft className="h-5 w-5 text-sage-600" />
                    ) : activeMode === 'ask' ? (
                      <MessageCircle className="h-5 w-5 text-sage-600" />
                    ) : (
                      <PenTool className="h-5 w-5 text-sage-600" />
                    )}
                    <span className="font-medium text-stone-900">{modeName(activeMode)}</span>
                  </div>
                  <button
                    onClick={() => {
                      setActiveMode(null)
                      setConversationId(null)
                      setMessages([])
                      setInput('')
                    }}
                    className="inline-flex items-center px-3 py-1.5 text-sm text-stone-600 border rounded-lg hover:bg-stone-50 transition"
                  >
                    <X className="h-4 w-4 mr-1.5" />
                    End Session
                  </button>
                </div>

                {/* Messages */}
                <div className="max-h-[500px] overflow-y-auto space-y-3 mb-4 pr-1">
                  {messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${
                          msg.role === 'user'
                            ? 'bg-sage-700 text-white'
                            : 'bg-stone-100 text-stone-800'
                        }`}
                      >
                        {msg.role === 'assistant' ? (
                          <div className="prose prose-sm prose-stone max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_strong]:font-semibold [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1 [&_h4]:text-sm [&_h4]:font-semibold [&_h4]:mt-2 [&_h4]:mb-1 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_p]:my-1.5">
                            <Markdown>{msg.content}</Markdown>
                          </div>
                        ) : (
                          <pre className="whitespace-pre-wrap font-sans leading-relaxed">{msg.content}</pre>
                        )}
                      </div>
                    </div>
                  ))}
                  {sending && (
                    <div className="flex justify-start">
                      <div className="bg-stone-100 text-stone-800 rounded-lg px-4 py-3">
                        <Loader2 className="h-4 w-4 animate-spin text-stone-400" />
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Input area */}
                <div className="flex items-end gap-3 border-t pt-4">
                  <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={activeMode === 'multiple_choice' ? 2 : 6}
                    placeholder={
                      activeMode === 'multiple_choice'
                        ? 'Type your answer... (Enter to send)'
                        : 'Write your essay response...'
                    }
                    disabled={sending}
                    className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-sage-200 focus:border-sage-500 outline-none resize-none text-stone-800 text-sm disabled:bg-stone-50"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={sending || !input.trim()}
                    className="p-2.5 bg-sage-700 text-white rounded-lg hover:bg-sage-600 disabled:bg-stone-300 disabled:cursor-not-allowed transition flex-shrink-0"
                    title="Send"
                  >
                    {sending ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Send className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* No content warning */}
        {!hasContent && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-5 mb-6">
            <p className="text-yellow-800 text-sm font-medium">
              This outline does not have extracted text content. AI Study Tools are unavailable.
            </p>
          </div>
        )}

        {/* Login prompt */}
        {!isLoggedIn && hasContent && (
          <div className="bg-stone-100 border border-stone-200 rounded-xl p-5 mb-6 text-center">
            <MessageSquare className="h-8 w-8 text-stone-400 mx-auto mb-2" />
            <p className="text-stone-700 font-medium mb-1">Sign in to use AI Study Tools</p>
            <p className="text-stone-500 text-sm mb-4">
              Practice with multiple choice quizzes and essay prompts generated from this outline.
            </p>
            <Link
              href={`/login?returnTo=${encodeURIComponent(`/outline/${outlineId}`)}`}
              className="inline-flex items-center px-4 py-2 bg-sage-700 text-white rounded-lg text-sm font-medium hover:bg-sage-600 transition"
            >
              Sign in to study
            </Link>
          </div>
        )}
      </main>
    </div>
  )
}
