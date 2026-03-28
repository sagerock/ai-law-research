'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Sparkles, Download, Copy, Check, AlertCircle, MessageSquare } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import { FormattedMessage } from '@/components/FormattedMessage'
import type { ToolProject } from '@/types'

interface SharedChatProps {
  toolType: string
  project: ToolProject
  onProjectUpdate: (project: ToolProject) => void
  generateLabel?: string
  regenerateLabel?: string
  documentLabel?: string
  chatPlaceholder?: string
  presetPrompts?: { label: string; prompt: string }[]
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export default function SharedChat({
  toolType,
  project,
  onProjectUpdate,
  generateLabel = 'Generate Document',
  regenerateLabel = 'Regenerate Document',
  documentLabel = 'Generated Document',
  chatPlaceholder = 'Ask about your document, request revisions, or get suggestions...',
  presetPrompts = [],
}: SharedChatProps) {
  const { session, getAccessToken } = useAuth()

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generatingText, setGeneratingText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [showDocument, setShowDocument] = useState(!!project.generated_document)

  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const parseSSE = async (res: Response, onText: (t: string) => void, onDone: (event: any, fullText: string) => void) => {
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let accumulated = ''
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6).trim())
          if (event.type === 'conversation_id') {
            setConversationId(event.conversation_id)
          } else if (event.type === 'text') {
            accumulated += event.text
            onText(accumulated)
          } else if (event.type === 'done') {
            onDone(event, accumulated)
          } else if (event.type === 'error') {
            setError(event.error)
          }
        } catch {}
      }
    }
  }

  const sendMessage = async (content: string) => {
    if (!content.trim() || streaming) return

    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content }])
    setInput('')
    setStreaming(true)
    setStreamingText('')

    try {
      const token = await getAccessToken()
      if (!token) { setError('Please sign in'); setStreaming(false); return }

      const res = await fetch(`${API_URL}/api/v1/tools/${toolType}/projects/${project.id}/chat`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, conversation_id: conversationId }),
      })

      if (res.status === 402) { setError('Community AI pool is empty. Add your own API key or donate to refill.'); setStreaming(false); return }
      if (!res.ok) { const data = await res.json().catch(() => ({})); setError(data.detail || 'Failed to send'); setStreaming(false); return }

      await parseSSE(
        res,
        (text) => setStreamingText(text),
        (_event, fullText) => {
          setMessages((prev) => [...prev, { role: 'assistant', content: fullText }])
          setStreamingText('')
        }
      )
    } catch (e: any) {
      setError(e.message || 'Connection error')
    } finally {
      setStreaming(false)
    }
  }

  const generateDocument = async () => {
    setError(null)
    setGenerating(true)
    setGeneratingText('')
    setShowDocument(true)

    try {
      const token = await getAccessToken()
      if (!token) { setError('Please sign in'); setGenerating(false); return }

      const res = await fetch(`${API_URL}/api/v1/tools/${toolType}/projects/${project.id}/generate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.status === 402) { setError('Community AI pool is empty.'); setGenerating(false); return }
      if (!res.ok) { const data = await res.json().catch(() => ({})); setError(data.detail || 'Generation failed'); setGenerating(false); return }

      await parseSSE(
        res,
        (text) => setGeneratingText(text),
        (event, fullText) => {
          onProjectUpdate({
            ...project,
            generated_document: fullText,
            status: 'complete',
            document_metadata: {
              input_tokens: event.input_tokens,
              output_tokens: event.output_tokens,
              cost: event.cost,
            },
          })
        }
      )
    } catch (e: any) {
      setError(e.message || 'Connection error')
    } finally {
      setGenerating(false)
    }
  }

  const exportDocx = async () => {
    try {
      const token = await getAccessToken()
      if (!token) { setError('Please sign in'); return }
      const res = await fetch(`${API_URL}/api/v1/tools/${toolType}/projects/${project.id}/export`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Export failed')

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = res.headers.get('content-disposition')?.match(/filename="(.+)"/)?.[1] || 'document.docx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      setError(e.message || 'Export failed')
    }
  }

  const copyDocument = () => {
    const text = project.generated_document || generatingText
    if (text) {
      navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const docText = project.generated_document || generatingText

  return (
    <div className="space-y-4">
      {/* Generate button */}
      <div className="bg-white rounded-xl border border-stone-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
            <Sparkles className="h-5 w-5 text-sage-700" />
          </div>
          <div>
            <h2 className="text-lg font-medium text-stone-900">AI Drafting & Generation</h2>
            <p className="text-sm text-stone-500">Chat with AI to refine, then generate the full document</p>
          </div>
        </div>

        <button
          onClick={generateDocument}
          disabled={generating}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-sage-700 text-white rounded-lg hover:bg-sage-600 transition-colors disabled:opacity-50 font-medium"
        >
          {generating ? (
            <><Loader2 className="h-5 w-5 animate-spin" /> Generating...</>
          ) : (
            <><Sparkles className="h-5 w-5" /> {project.generated_document ? regenerateLabel : generateLabel}</>
          )}
        </button>

        {error && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />{error}
          </div>
        )}
      </div>

      {/* Generated document preview */}
      {showDocument && docText && (
        <div className="bg-white rounded-xl border border-stone-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-stone-900">{documentLabel}</h3>
            <div className="flex items-center gap-2">
              <button onClick={copyDocument} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-stone-600 hover:bg-stone-100 rounded-lg transition-colors">
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
              {project.generated_document && (
                <button onClick={exportDocx} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-sage-700 text-white rounded-lg hover:bg-sage-600 transition-colors">
                  <Download className="h-3.5 w-3.5" /> Export DOCX
                </button>
              )}
            </div>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
            <p className="text-xs text-amber-700 font-medium">EDUCATIONAL DOCUMENT — NOT FOR FILING</p>
          </div>

          <div className="prose prose-sm max-w-none prose-stone">
            <FormattedMessage content={docText} />
          </div>

          {generating && (
            <div className="flex items-center gap-2 mt-4 text-sm text-sage-600">
              <Loader2 className="h-4 w-4 animate-spin" /> Generating...
            </div>
          )}

          {project.document_metadata?.cost && (
            <p className="text-xs text-stone-400 mt-4">
              Cost: ${project.document_metadata.cost.toFixed(4)} &middot;{' '}
              {project.document_metadata.input_tokens?.toLocaleString()} in / {project.document_metadata.output_tokens?.toLocaleString()} out
            </p>
          )}
        </div>
      )}

      {/* Chat section */}
      <div className="bg-white rounded-xl border border-stone-200 p-6">
        <div className="flex items-center gap-3 mb-4">
          <MessageSquare className="h-5 w-5 text-sage-700" />
          <h3 className="font-medium text-stone-900">Refine with AI</h3>
        </div>

        {messages.length === 0 && presetPrompts.length > 0 && (
          <div className="grid grid-cols-2 gap-2 mb-4">
            {presetPrompts.map((p) => (
              <button
                key={p.label}
                onClick={() => sendMessage(p.prompt)}
                disabled={streaming}
                className="text-left px-3 py-2 text-xs text-stone-600 bg-stone-50 hover:bg-sage-50 hover:text-sage-700 rounded-lg border border-stone-200 transition-colors disabled:opacity-50"
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        {messages.length > 0 && (
          <div className="max-h-96 overflow-y-auto space-y-4 mb-4 pr-2">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-lg px-4 py-3 text-sm ${msg.role === 'user' ? 'bg-sage-700 text-white' : 'bg-stone-50 text-stone-700'}`}>
                  {msg.role === 'assistant' ? <FormattedMessage content={msg.content} /> : msg.content}
                </div>
              </div>
            ))}
            {streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-lg px-4 py-3 text-sm bg-stone-50 text-stone-700">
                  <FormattedMessage content={streamingText} />
                </div>
              </div>
            )}
            {streaming && !streamingText && (
              <div className="flex justify-start">
                <div className="rounded-lg px-4 py-3 bg-stone-50">
                  <Loader2 className="h-4 w-4 animate-spin text-sage-600" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}

        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input) } }}
            placeholder={chatPlaceholder}
            rows={2}
            disabled={streaming}
            className="flex-1 px-3 py-2 border border-stone-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent resize-none disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || streaming}
            className="px-3 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 transition-colors disabled:opacity-50 self-end"
          >
            {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  )
}
