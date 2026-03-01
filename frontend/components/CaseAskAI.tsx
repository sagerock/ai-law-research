'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Sparkles, ChevronDown, ChevronUp, Send, Loader2, AlertCircle, LogIn, Copy, Check } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { useRouter } from 'next/navigation'
import { API_URL } from '@/lib/api'
import { FormattedMessage } from '@/components/FormattedMessage'
import type { ChatMessageType, UsageInfo } from '@/types'

interface CaseAskAIProps {
  caseId: string
  caseTitle: string
}

export default function CaseAskAI({ caseId, caseTitle }: CaseAskAIProps) {
  const { user, session, getAccessToken } = useAuth()
  const router = useRouter()

  const [expanded, setExpanded] = useState(false)
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [rateLimited, setRateLimited] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [usage, setUsage] = useState<UsageInfo | null>(null)
  const [usageLoaded, setUsageLoaded] = useState(false)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const inputRef = useRef<HTMLTextAreaElement>(null)

  const getFreshAuthHeaders = useCallback(async (): Promise<Record<string, string>> => {
    const token = await getAccessToken()
    if (!token) return {}
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  }, [getAccessToken])

  // Fetch usage when section expands and user is signed in
  useEffect(() => {
    if (expanded && user && session?.access_token && !usageLoaded) {
      fetchUsage()
    }
  }, [expanded, user, session?.access_token])

  // Auto-scroll chat container (not the page) on new messages
  const chatContainerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight
    }
  }, [messages, streamingText])

  const fetchUsage = async () => {
    try {
      const headers = await getFreshAuthHeaders()
      const res = await fetch(`${API_URL}/api/v1/study/usage`, {
        headers,
      })
      if (res.ok) {
        const data = await res.json()
        setUsage(data)
        setUsageLoaded(true)
        setRateLimited(data.tier === 'free' && data.messages_remaining === 0)
      }
    } catch (e) {
      console.error('Failed to fetch usage:', e)
    }
  }

  const sendMessage = async () => {
    const content = input.trim()
    if (!content || streaming || rateLimited) return

    setInput('')
    setStreaming(true)
    setStreamingText('')
    setError(null)

    const tempUserMsg: ChatMessageType = {
      id: Date.now(),
      role: 'user',
      content,
      model: null,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, tempUserMsg])

    try {
      const headers = await getFreshAuthHeaders()
      if (!headers['Authorization']) {
        setError('Your session has expired. Please sign in again.')
        setStreaming(false)
        return
      }

      const res = await fetch(`${API_URL}/api/v1/cases/${caseId}/ask`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          content,
          conversation_id: conversationId,
        }),
      })

      if (res.status === 429) {
        setRateLimited(true)
        setStreaming(false)
        return
      }

      if (res.status === 401) {
        setError('Your session has expired. Please sign in again.')
        setStreaming(false)
        return
      }

      if (!res.ok || !res.body) {
        setError('Something went wrong. Please try again.')
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
              if (!conversationId && event.conversation_id) {
                setConversationId(event.conversation_id)
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
      console.error('Case ask error:', e)
    } finally {
      setStreaming(false)
      setStreamingText('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div>
      {/* Header / Toggle */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-sage-600" />
          <h2 className="text-lg font-semibold text-stone-900">Ask AI About This Case</h2>
        </div>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-stone-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-stone-400" />
        )}
      </button>

      {expanded && (
        <div className="mt-4">
          {/* Not signed in */}
          {!user ? (
            <div className="bg-stone-50 rounded-lg p-6 text-center">
              <p className="text-stone-600 mb-3">Sign in to ask AI questions about this case</p>
              <button
                onClick={() => router.push('/login')}
                className="inline-flex items-center gap-2 px-4 py-2 bg-sage-700 hover:bg-sage-600 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <LogIn className="h-4 w-4" />
                Sign In
              </button>
            </div>
          ) : (
            <>
              {/* Rate limit banner */}
              {rateLimited && (
                <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg mb-3 text-sm text-amber-800">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>Daily message limit reached. Upgrade to Pro for unlimited messages.</span>
                </div>
              )}

              {/* Error banner */}
              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg mb-3 text-sm text-red-800">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Messages */}
              <div ref={chatContainerRef} className="max-h-[500px] overflow-y-auto space-y-3 mb-3">
                {messages.length === 0 && !streaming && (
                  <p className="text-sm text-stone-500 italic">
                    Ask a question about <strong>{caseTitle}</strong> — e.g. &quot;What was the dissent&apos;s argument?&quot; or &quot;How does this relate to Marbury v. Madison?&quot;
                  </p>
                )}

                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[85%] ${msg.role === 'assistant' ? '' : ''}`}>
                      <div
                        className={`rounded-lg px-3 py-2 text-sm ${
                          msg.role === 'user'
                            ? 'bg-sage-700 text-white'
                            : 'bg-stone-100 text-stone-900'
                        }`}
                      >
                        {msg.role === 'assistant' ? (
                          <FormattedMessage content={msg.content} />
                        ) : (
                          msg.content
                        )}
                      </div>
                      {msg.role === 'assistant' && (
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(msg.content)
                            setCopiedId(msg.id)
                            setTimeout(() => setCopiedId(null), 2000)
                          }}
                          className="flex items-center gap-1 mt-1 ml-1 text-xs text-stone-400
                                     hover:text-stone-600 transition-colors"
                        >
                          {copiedId === msg.id ? (
                            <><Check className="h-3 w-3 text-green-500" /> Copied</>
                          ) : (
                            <><Copy className="h-3 w-3" /> Copy</>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {/* Streaming indicator */}
                {streaming && streamingText && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-stone-100 text-stone-900">
                      <FormattedMessage content={streamingText} />
                    </div>
                  </div>
                )}
                {streaming && !streamingText && (
                  <div className="flex justify-start">
                    <div className="rounded-lg px-3 py-2 bg-stone-100">
                      <Loader2 className="h-4 w-4 animate-spin text-stone-400" />
                    </div>
                  </div>
                )}

              </div>

              {/* Input */}
              <div className="flex gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={rateLimited ? 'Daily limit reached' : `Ask about ${caseTitle}...`}
                  disabled={streaming || rateLimited}
                  rows={1}
                  className="flex-1 resize-none rounded-lg border border-stone-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sage-200 focus:border-sage-400 disabled:opacity-50 disabled:bg-stone-50"
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || streaming || rateLimited}
                  className="px-3 py-2 bg-sage-700 hover:bg-sage-600 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {streaming ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </button>
              </div>

              {/* Usage counter */}
              {usage && usage.messages_remaining !== null && (
                <p className="text-xs text-stone-400 mt-2 text-right">
                  {usage.messages_remaining}/{usage.daily_limit || 15} messages remaining today
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
