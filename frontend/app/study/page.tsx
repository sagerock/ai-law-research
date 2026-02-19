'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Scale, GraduationCap, Upload, MessageCircle,
  Send, Plus, Trash2, FileText, Check, X, Loader2, Menu, ChevronRight,
  ChevronDown, AlertCircle
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { UserMenu } from '@/components/auth/UserMenu'
import type { StudyNote, Conversation, ChatMessageType, UsageInfo, TagCount } from '@/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function StudyPage() {
  const router = useRouter()
  const { user, session, isLoading: authLoading } = useAuth()

  // State
  const [notes, setNotes] = useState<StudyNote[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversation, setActiveConversation] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [selectedNoteIds, setSelectedNoteIds] = useState<number[]>([])
  const [usage, setUsage] = useState<UsageInfo | null>(null)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [showUpload, setShowUpload] = useState(false)
  const [showSidebar, setShowSidebar] = useState(false)
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())
  const [uploading, setUploading] = useState(false)
  const [rateLimited, setRateLimited] = useState(false)
  const [availableTags, setAvailableTags] = useState<TagCount[]>([])

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const getAuthHeaders = useCallback((): Record<string, string> => {
    if (!session?.access_token) return {}
    return {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json',
    }
  }, [session?.access_token])

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [authLoading, user, router])

  // Load data once authenticated
  useEffect(() => {
    if (user && session?.access_token) {
      fetchNotes()
      fetchConversations()
      fetchUsage()
      fetchTags()
    }
  }, [user, session?.access_token])

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const fetchNotes = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/notes`, {
        headers: getAuthHeaders(),
      })
      if (res.ok) setNotes(await res.json())
    } catch (e) {
      console.error('Failed to fetch notes:', e)
    }
  }

  const fetchTags = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/tags`, {
        headers: getAuthHeaders(),
      })
      if (res.ok) setAvailableTags(await res.json())
    } catch (e) {
      console.error('Failed to fetch tags:', e)
    }
  }

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/conversations`, {
        headers: getAuthHeaders(),
      })
      if (res.ok) setConversations(await res.json())
    } catch (e) {
      console.error('Failed to fetch conversations:', e)
    }
  }

  const fetchUsage = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/usage`, {
        headers: getAuthHeaders(),
      })
      if (res.ok) {
        const data = await res.json()
        setUsage(data)
        setRateLimited(data.tier === 'free' && data.messages_remaining === 0)
      }
    } catch (e) {
      console.error('Failed to fetch usage:', e)
    }
  }

  const loadConversation = async (conversationId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/conversations/${conversationId}`, {
        headers: getAuthHeaders(),
      })
      if (res.ok) {
        const data = await res.json()
        setActiveConversation(conversationId)
        setMessages(data.messages || [])
        setSelectedNoteIds(data.note_ids || [])
        setShowSidebar(false)
      }
    } catch (e) {
      console.error('Failed to load conversation:', e)
    }
  }

  const deleteNote = async (noteId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/notes/${noteId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      if (res.ok) {
        setNotes(prev => prev.filter(n => n.id !== noteId))
        setSelectedNoteIds(prev => prev.filter(id => id !== noteId))
      }
    } catch (e) {
      console.error('Failed to delete note:', e)
    }
  }

  const deleteConversation = async (conversationId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== conversationId))
        if (activeConversation === conversationId) {
          setActiveConversation(null)
          setMessages([])
        }
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e)
    }
  }

  const handleUpload = async (file: File, title: string, tags: string[]) => {
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', title)
      if (tags.length > 0) formData.append('tags', tags.join(','))

      const res = await fetch(`${API_URL}/api/v1/study/notes/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session?.access_token}`,
        },
        body: formData,
      })

      if (res.ok) {
        const note = await res.json()
        setNotes(prev => [note, ...prev])
        setShowUpload(false)
        fetchTags()
      } else {
        const err = await res.json()
        alert(err.detail || 'Upload failed')
      }
    } catch (e) {
      console.error('Upload failed:', e)
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const sendMessage = async () => {
    const content = input.trim()
    if (!content || streaming) return

    if (rateLimited) return

    setInput('')
    setStreaming(true)
    setStreamingText('')

    // Optimistic UI: add user message
    const tempUserMsg: ChatMessageType = {
      id: Date.now(),
      role: 'user',
      content,
      model: null,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, tempUserMsg])

    try {
      const res = await fetch(`${API_URL}/api/v1/study/chat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          content,
          conversation_id: activeConversation,
          note_ids: selectedNoteIds.length > 0 ? selectedNoteIds : undefined,
        }),
      })

      if (res.status === 429) {
        setRateLimited(true)
        setStreaming(false)
        return
      }

      if (!res.ok || !res.body) {
        setStreaming(false)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let accumulatedText = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const dataStr = line.slice(6).trim()
          if (!dataStr) continue

          try {
            const event = JSON.parse(dataStr)
            if (event.type === 'text') {
              accumulatedText += event.text
              setStreamingText(accumulatedText)
            } else if (event.type === 'done') {
              const convoId = event.conversation_id
              if (!activeConversation && convoId) {
                setActiveConversation(convoId)
                fetchConversations()
              }
              if (event.messages_remaining !== null && event.messages_remaining !== undefined) {
                setUsage(prev => prev ? {
                  ...prev,
                  messages_today: prev.messages_today + 1,
                  messages_remaining: event.messages_remaining,
                } : prev)
                if (event.messages_remaining === 0) setRateLimited(true)
              }
            } else if (event.type === 'error') {
              accumulatedText += `\n\n*Error: ${event.error}*`
              setStreamingText(accumulatedText)
            }
          } catch {
            // Skip malformed JSON
          }
        }
      }

      // Finalize: add assistant message
      if (accumulatedText) {
        const assistantMsg: ChatMessageType = {
          id: Date.now() + 1,
          role: 'assistant',
          content: accumulatedText,
          model: usage?.model || null,
          created_at: new Date().toISOString(),
        }
        setMessages(prev => [...prev, assistantMsg])
      }
    } catch (e) {
      console.error('Chat error:', e)
    } finally {
      setStreaming(false)
      setStreamingText('')
    }
  }

  const startNewChat = () => {
    setActiveConversation(null)
    setMessages([])
    setStreamingText('')
    setShowSidebar(false)
    inputRef.current?.focus()
  }

  const toggleNoteSelection = (noteId: number) => {
    setSelectedNoteIds(prev =>
      prev.includes(noteId)
        ? prev.filter(id => id !== noteId)
        : [...prev, noteId]
    )
  }

  const toggleGroupCollapsed = (group: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev)
      if (next.has(group)) next.delete(group)
      else next.add(group)
      return next
    })
  }

  const toggleGroupSelection = (groupNoteIds: number[]) => {
    const allSelected = groupNoteIds.every(id => selectedNoteIds.includes(id))
    if (allSelected) {
      setSelectedNoteIds(prev => prev.filter(id => !groupNoteIds.includes(id)))
    } else {
      setSelectedNoteIds(prev => [...new Set([...prev, ...groupNoteIds])])
    }
  }

  // Group notes by tags (notes with multiple tags appear in all matching groups)
  const noteGroups = useMemo(() => {
    const groups: Record<string, StudyNote[]> = {}
    for (const note of notes) {
      const tagList = note.tags?.length ? note.tags : ['Uncategorized']
      for (const tag of tagList) {
        if (!groups[tag]) groups[tag] = []
        groups[tag].push(note)
      }
    }
    // Sort groups alphabetically, Uncategorized last
    return Object.entries(groups).sort(([a], [b]) => {
      if (a === 'Uncategorized') return 1
      if (b === 'Uncategorized') return -1
      return a.localeCompare(b)
    })
  }, [notes])

  // Loading state
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-neutral-100 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-neutral-400" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-neutral-100 flex flex-col">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Law Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free Case Briefs for Law Students</p>
              </div>
            </Link>
            <nav className="flex items-center space-x-4 sm:space-x-6">
              <Link
                href="/study"
                className="text-neutral-900 font-medium flex items-center"
              >
                <GraduationCap className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Study</span>
              </Link>
              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
                title="Discord"
              >
                <MessageCircle className="h-5 w-5" />
              </a>
              <UserMenu />
            </nav>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Mobile sidebar toggle */}
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          className="md:hidden fixed bottom-4 left-4 z-40 bg-blue-600 text-white p-3 rounded-full shadow-lg"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Sidebar */}
        <div className={`${showSidebar ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0 transition-transform fixed md:static inset-y-0 left-0 z-30 w-72 bg-white border-r flex flex-col mt-[73px] md:mt-0`}>
          {/* New Chat button */}
          <div className="p-3 border-b">
            <button
              onClick={startNewChat}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {/* Notes section */}
            <div className="p-3 border-b">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                  My Notes
                </h3>
                <button
                  onClick={() => setShowUpload(true)}
                  className="text-blue-600 hover:text-blue-700"
                  title="Upload note"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>

              {notes.length === 0 ? (
                <p className="text-xs text-neutral-400 py-2">No notes yet. Upload one to get started.</p>
              ) : (
                <div className="space-y-0.5">
                  {noteGroups.map(([group, groupNotes]) => {
                    const groupNoteIds = groupNotes.map(n => n.id)
                    const allSelected = groupNoteIds.every(id => selectedNoteIds.includes(id))
                    const someSelected = groupNoteIds.some(id => selectedNoteIds.includes(id))
                    const isCollapsed = collapsedGroups.has(group)

                    return (
                      <div key={group}>
                        {/* Group header */}
                        <div className="flex items-center gap-1.5 py-1.5 px-2 rounded hover:bg-neutral-50 cursor-pointer">
                          <button
                            onClick={() => toggleGroupCollapsed(group)}
                            className="text-neutral-400 hover:text-neutral-600"
                          >
                            {isCollapsed ? (
                              <ChevronRight className="h-3.5 w-3.5" />
                            ) : (
                              <ChevronDown className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <input
                            type="checkbox"
                            checked={allSelected}
                            ref={(el) => { if (el) el.indeterminate = someSelected && !allSelected }}
                            onChange={() => toggleGroupSelection(groupNoteIds)}
                            className="h-3.5 w-3.5 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span
                            onClick={() => toggleGroupCollapsed(group)}
                            className="flex-1 text-xs font-semibold text-neutral-600 uppercase tracking-wide truncate"
                          >
                            {group}
                          </span>
                          <span className="text-xs text-neutral-400">{groupNotes.length}</span>
                        </div>

                        {/* Notes in group */}
                        {!isCollapsed && (
                          <div className="ml-5 space-y-0.5">
                            {groupNotes.map(note => (
                              <div
                                key={note.id}
                                className="flex items-center gap-2 py-1 px-2 rounded hover:bg-neutral-50 group"
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedNoteIds.includes(note.id)}
                                  onChange={() => toggleNoteSelection(note.id)}
                                  className="h-3.5 w-3.5 rounded border-neutral-300 text-blue-600 focus:ring-blue-500"
                                />
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm text-neutral-800 truncate">{note.title}</p>
                                  <div className="flex items-center gap-1 flex-wrap">
                                    <span className="text-xs text-neutral-400">
                                      {note.char_count.toLocaleString()} chars
                                    </span>
                                    {(note.tags || []).filter(t => t !== group).map(t => (
                                      <span key={t} className="text-[10px] bg-neutral-100 text-neutral-500 px-1.5 py-0 rounded-full">{t}</span>
                                    ))}
                                  </div>
                                </div>
                                <button
                                  onClick={() => deleteNote(note.id)}
                                  className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-red-500 transition"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Conversations section */}
            <div className="p-3">
              <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
                Conversations
              </h3>
              {conversations.length === 0 ? (
                <p className="text-xs text-neutral-400 py-2">No conversations yet.</p>
              ) : (
                <div className="space-y-1">
                  {conversations.map(convo => (
                    <div
                      key={convo.id}
                      onClick={() => loadConversation(convo.id)}
                      className={`flex items-center gap-2 py-1.5 px-2 rounded cursor-pointer group ${
                        activeConversation === convo.id
                          ? 'bg-blue-50 text-blue-700'
                          : 'hover:bg-neutral-50 text-neutral-700'
                      }`}
                    >
                      <MessageCircle className="h-3.5 w-3.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{convo.title || 'Untitled'}</p>
                        <p className="text-xs text-neutral-400">
                          {convo.message_count || 0} msgs
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteConversation(convo.id)
                        }}
                        className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-red-500 transition"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Usage info at bottom of sidebar */}
          {usage && (
            <div className="p-3 border-t text-xs text-neutral-500">
              <div className="flex items-center justify-between">
                <span className="capitalize">{usage.tier} tier</span>
                {usage.tier === 'free' && (
                  <span>{usage.messages_remaining}/{usage.daily_limit} left today</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && !streaming && (
              <div className="flex-1 flex items-center justify-center h-full">
                <div className="text-center py-20">
                  <GraduationCap className="h-16 w-16 mx-auto mb-4 text-neutral-300" />
                  <h2 className="text-xl font-semibold text-neutral-700 mb-2">
                    AI Study Assistant
                  </h2>
                  <p className="text-neutral-500 max-w-md mx-auto mb-4">
                    Upload your class notes, select them in the sidebar, then ask questions.
                    The AI will reference your notes and our case brief database.
                  </p>
                  {selectedNoteIds.length > 0 && (
                    <p className="text-sm text-blue-600">
                      <Check className="h-4 w-4 inline mr-1" />
                      {selectedNoteIds.length} note{selectedNoteIds.length > 1 ? 's' : ''} selected
                    </p>
                  )}
                </div>
              </div>
            )}

            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border text-neutral-800'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    {msg.role === 'assistant' ? (
                      <FormattedMessage content={msg.content} />
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Streaming response */}
            {streaming && streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-lg px-4 py-3 bg-white border text-neutral-800">
                  <div className="text-sm whitespace-pre-wrap leading-relaxed">
                    <FormattedMessage content={streamingText} />
                    <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-0.5" />
                  </div>
                </div>
              </div>
            )}

            {streaming && !streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-lg px-4 py-3 bg-white border">
                  <Loader2 className="h-5 w-5 animate-spin text-neutral-400" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Rate limit banner */}
          {rateLimited && (
            <div className="mx-4 mb-2 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-800">Daily limit reached</p>
                <p className="text-xs text-amber-600 mt-0.5">
                  Free tier includes 15 messages per day. Contact us to upgrade to Pro for unlimited messages.
                </p>
              </div>
            </div>
          )}

          {/* Input area */}
          <div className="border-t bg-white p-4">
            <div className="flex items-end gap-2 max-w-4xl mx-auto">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    sendMessage()
                  }
                }}
                placeholder={rateLimited ? 'Daily limit reached...' : 'Ask about your notes or any legal topic...'}
                disabled={streaming || rateLimited}
                rows={1}
                className="flex-1 resize-none rounded-lg border border-neutral-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-neutral-50 disabled:text-neutral-400"
                style={{ minHeight: '42px', maxHeight: '120px' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement
                  target.style.height = 'auto'
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px'
                }}
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || streaming || rateLimited}
                className="flex-shrink-0 p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:bg-neutral-300 disabled:cursor-not-allowed transition"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
            {usage && usage.tier === 'free' && !rateLimited && (
              <p className="text-xs text-neutral-400 text-center mt-2">
                {usage.messages_remaining}/{usage.daily_limit} messages remaining today
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUpload={handleUpload}
          uploading={uploading}
          availableTags={availableTags}
        />
      )}

      {/* Sidebar overlay for mobile */}
      {showSidebar && (
        <div
          className="md:hidden fixed inset-0 bg-black/30 z-20"
          onClick={() => setShowSidebar(false)}
        />
      )}
    </div>
  )
}

// --- Upload Modal ---
function UploadModal({
  onClose,
  onUpload,
  uploading,
  availableTags,
}: {
  onClose: () => void
  onUpload: (file: File, title: string, tags: string[]) => void
  uploading: boolean
  availableTags: TagCount[]
}) {
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const tagInputRef = useRef<HTMLInputElement>(null)

  const handleFile = (f: File) => {
    const ext = f.name.split('.').pop()?.toLowerCase()
    if (!['pdf', 'docx', 'txt'].includes(ext || '')) {
      alert('Only PDF, DOCX, and TXT files are supported')
      return
    }
    if (f.size > 10 * 1024 * 1024) {
      alert('File size limit is 10MB')
      return
    }
    setFile(f)
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ''))
  }

  const addTag = (tag: string) => {
    const trimmed = tag.trim()
    if (trimmed && !selectedTags.includes(trimmed)) {
      setSelectedTags(prev => [...prev, trimmed])
    }
    setTagInput('')
    setShowDropdown(false)
    tagInputRef.current?.focus()
  }

  const removeTag = (tag: string) => {
    setSelectedTags(prev => prev.filter(t => t !== tag))
  }

  const filteredTags = availableTags.filter(
    tc => !selectedTags.includes(tc.tag) &&
      tc.tag.toLowerCase().includes(tagInput.toLowerCase())
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-900">Upload Study Note</h2>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            const f = e.dataTransfer.files[0]
            if (f) handleFile(f)
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition mb-4 ${
            dragOver
              ? 'border-blue-500 bg-blue-50'
              : file
              ? 'border-green-300 bg-green-50'
              : 'border-neutral-300 hover:border-neutral-400'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleFile(f)
            }}
          />
          {file ? (
            <div>
              <Check className="h-8 w-8 mx-auto mb-2 text-green-600" />
              <p className="text-sm font-medium text-neutral-800">{file.name}</p>
              <p className="text-xs text-neutral-500 mt-1">
                {(file.size / 1024).toFixed(0)} KB
              </p>
            </div>
          ) : (
            <div>
              <FileText className="h-8 w-8 mx-auto mb-2 text-neutral-400" />
              <p className="text-sm text-neutral-600">
                Drag & drop or click to select
              </p>
              <p className="text-xs text-neutral-400 mt-1">
                PDF, DOCX, or TXT (max 10MB)
              </p>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-neutral-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Property Law - Week 5 Notes"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">Tags (optional)</label>
            <div
              className="w-full border border-neutral-300 rounded-lg px-2 py-1.5 flex flex-wrap items-center gap-1.5 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent min-h-[38px] cursor-text"
              onClick={() => tagInputRef.current?.focus()}
            >
              {selectedTags.map(tag => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded-full"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); removeTag(tag) }}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
              <div className="relative flex-1 min-w-[80px]">
                <input
                  ref={tagInputRef}
                  value={tagInput}
                  onChange={(e) => {
                    setTagInput(e.target.value)
                    setShowDropdown(true)
                  }}
                  onFocus={() => setShowDropdown(true)}
                  onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ',') && tagInput.trim()) {
                      e.preventDefault()
                      addTag(tagInput)
                    } else if (e.key === 'Backspace' && !tagInput && selectedTags.length > 0) {
                      removeTag(selectedTags[selectedTags.length - 1])
                    }
                  }}
                  className="w-full border-0 outline-none text-sm py-0.5 bg-transparent"
                  placeholder={selectedTags.length === 0 ? 'e.g. Property Law, Torts' : ''}
                />
                {showDropdown && tagInput && filteredTags.length > 0 && (
                  <div className="absolute left-0 right-0 top-full mt-1 bg-white border border-neutral-200 rounded-lg shadow-lg z-10 max-h-40 overflow-y-auto">
                    {filteredTags.map(tc => (
                      <button
                        key={tc.tag}
                        type="button"
                        onMouseDown={(e) => { e.preventDefault(); addTag(tc.tag) }}
                        className="w-full text-left px-3 py-1.5 text-sm hover:bg-blue-50 flex items-center justify-between"
                      >
                        <span>{tc.tag}</span>
                        <span className="text-xs text-neutral-400">{tc.count} note{tc.count !== 1 ? 's' : ''}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (file && title.trim()) {
                onUpload(file, title.trim(), selectedTags)
              }
            }}
            disabled={!file || !title.trim() || uploading}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:bg-neutral-300 disabled:cursor-not-allowed transition flex items-center gap-2"
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Upload
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

// --- Formatted assistant message (basic markdown) ---
function FormattedMessage({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <>
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith('### ')) {
          return <h4 key={i} className="font-semibold text-neutral-900 mt-3 mb-1">{line.slice(4)}</h4>
        }
        if (line.startsWith('## ')) {
          return <h3 key={i} className="font-bold text-neutral-900 mt-3 mb-1">{line.slice(3)}</h3>
        }
        if (line.startsWith('# ')) {
          return <h2 key={i} className="text-lg font-bold text-neutral-900 mt-3 mb-1">{line.slice(2)}</h2>
        }
        // Bullet points
        if (line.match(/^[-*]\s/)) {
          return <p key={i} className="ml-4 before:content-['\2022'] before:mr-2 before:text-neutral-400">{formatInline(line.slice(2))}</p>
        }
        // Numbered list
        if (line.match(/^\d+\.\s/)) {
          return <p key={i} className="ml-4">{formatInline(line)}</p>
        }
        // Empty line
        if (!line.trim()) {
          return <br key={i} />
        }
        // Regular text
        return <p key={i}>{formatInline(line)}</p>
      })}
    </>
  )
}

function formatInline(text: string): React.ReactNode {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
    }
    return <span key={i}>{part}</span>
  })
}
