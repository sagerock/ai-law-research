'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Upload, ArrowLeft, Pause, Flame, Loader2 } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import Header from '@/components/Header'
import MindmapUpload from '@/components/study/MindmapUpload'
import MindmapTree from '@/components/study/MindmapTree'
import QuizCard from '@/components/study/QuizCard'
import ProgressPanel from '@/components/study/ProgressPanel'
import DopamineFlash from '@/components/study/DopamineFlash'
import type { Mindmap, MindmapNode, StudySession, NodeRef } from '@/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function StudySessionPage() {
  const router = useRouter()
  const { user, session: authSession, isLoading: authLoading } = useAuth()

  // Mindmap list state
  const [mindmaps, setMindmaps] = useState<Mindmap[]>([])
  const [showUpload, setShowUpload] = useState(false)
  const [loading, setLoading] = useState(true)

  // Active session state
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [activeMindmapId, setActiveMindmapId] = useState<number | null>(null)
  const [currentNodeId, setCurrentNodeId] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [breadcrumb, setBreadcrumb] = useState<string[]>([])
  const [nodeText, setNodeText] = useState('')
  const [caseRefs, setCaseRefs] = useState<NodeRef[]>([])
  const [ruleRefs, setRuleRefs] = useState<NodeRef[]>([])
  const [mode, setMode] = useState('quiz')
  const [streak, setStreak] = useState(0)
  const [maxStreak, setMaxStreak] = useState(0)
  const [nodesMastered, setNodesMastered] = useState(0)
  const [totalNodes, setTotalNodes] = useState(0)
  const [totalCorrect, setTotalCorrect] = useState(0)
  const [totalIncorrect, setTotalIncorrect] = useState(0)
  const [nodes, setNodes] = useState<MindmapNode[]>([])
  const [streaming, setStreaming] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  const [dopamineEvent, setDopamineEvent] = useState<string | null>(null)
  const [completed, setCompleted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSidebar, setShowSidebar] = useState(false)
  const [pendingNext, setPendingNext] = useState<any>(null)


  const submitTimeRef = useRef(Date.now())

  const getAuthHeaders = useCallback((): Record<string, string> => {
    if (!authSession?.access_token) return {}
    return {
      'Authorization': `Bearer ${authSession.access_token}`,
      'Content-Type': 'application/json',
    }
  }, [authSession?.access_token])

  // Load mindmaps
  useEffect(() => {
    if (authLoading || !user) return
    fetchMindmaps()
  }, [authLoading, user])

  const fetchMindmaps = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/mindmaps`, { headers: getAuthHeaders() })
      if (res.ok) setMindmaps(await res.json())
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  // Load mindmap nodes for tree when session starts
  const loadMindmapNodes = async (mindmapId: number) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/study/mindmaps/${mindmapId}`, { headers: getAuthHeaders() })
      if (res.ok) {
        const data = await res.json()
        setNodes(data.nodes || [])
      }
    } catch {
      // ignore
    }
  }

  // Apply session data to state
  const applySession = (data: StudySession) => {
    setSessionId(data.session_id)
    setCurrentNodeId(data.current_node_id)
    setQuestion(data.question)
    setBreadcrumb(data.breadcrumb || [])
    setNodeText(data.node_text || '')
    setCaseRefs(data.case_refs || [])
    setRuleRefs(data.rule_refs || [])
    setMode(data.mode || 'quiz')
    setStreak(data.streak || 0)
    setMaxStreak(data.max_streak || 0)
    setNodesMastered(data.nodes_mastered || 0)
    setTotalNodes(data.total_nodes || 0)
    setTotalCorrect(data.total_correct || 0)
    setTotalIncorrect(data.total_incorrect || 0)
    setFeedbackText('')
    setCompleted(false)
  }

  // Start session
  const startSession = async (mindmapId: number, branchNodeId?: string) => {
    setError(null)
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/study/session/start`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ mindmap_id: mindmapId, branch_node_id: branchNodeId }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Failed to start session' }))
        throw new Error(body.detail)
      }
      const data = await res.json()
      if (data.completed) {
        setCompleted(true)
        setActiveMindmapId(mindmapId)
      } else {
        setActiveMindmapId(mindmapId)
        applySession(data)
        loadMindmapNodes(mindmapId)
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Submit answer (SSE streaming)
  const handleSubmit = useCallback(async (answer: string) => {
    if (!sessionId || streaming) return
    setStreaming(true)
    setFeedbackText('')
    const responseTime = Date.now() - submitTimeRef.current

    try {
      const res = await fetch(`${API_URL}/api/v1/study/session/${sessionId}/respond`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ answer, response_time_ms: responseTime }),
      })

      if (!res.ok || !res.body) {
        setError('Failed to get response')
        setStreaming(false)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
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

            switch (event.type) {
              case 'feedback':
                setFeedbackText(prev => prev + (event.text || ''))
                break
              case 'progress':
                setStreak(event.streak ?? 0)
                setMaxStreak(event.max_streak ?? 0)
                setNodesMastered(event.mastered_count ?? 0)
                setTotalNodes(event.total_nodes ?? totalNodes)
                setTotalCorrect(event.total_correct ?? 0)
                setTotalIncorrect(event.total_incorrect ?? 0)
                // Update node mastery in tree
                if (currentNodeId) {
                  setNodes(prev => prev.map(n =>
                    n.node_id === currentNodeId
                      ? { ...n, mastery: event.mastery as MindmapNode['mastery'] }
                      : n
                  ))
                }
                break
              case 'dopamine':
                setDopamineEvent(event.event)
                break
              case 'next_question':
                // Store pending — user clicks "Next" to advance
                setPendingNext(event)
                break
              case 'complete':
                setCompleted(true)
                break
              case 'error':
                setError(event.error)
                break
              case 'done':
                break
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setStreaming(false)
    }
  }, [sessionId, streaming, getAuthHeaders, currentNodeId, totalNodes])

  // Skip
  const handleSkip = useCallback(async () => {
    if (!sessionId || streaming) return
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/study/session/${sessionId}/skip`, {
        method: 'POST',
        headers: getAuthHeaders(),
      })
      if (!res.ok) throw new Error('Failed to skip')
      const data = await res.json()
      if (data.completed) {
        setCompleted(true)
      } else {
        setCurrentNodeId(data.current_node_id)
        setQuestion(data.question)
        setBreadcrumb(data.breadcrumb || [])
        setNodeText(data.node_text || '')
        setCaseRefs(data.case_refs || [])
        setRuleRefs(data.rule_refs || [])
        setStreak(data.streak ?? 0)
        setNodesMastered(data.nodes_mastered ?? 0)
        setTotalNodes(data.total_nodes ?? totalNodes)
        setFeedbackText('')
        submitTimeRef.current = Date.now()
      }
    } catch (e: any) {
      setError(e.message)
    }
  }, [sessionId, streaming, getAuthHeaders, totalNodes])

  // Advance to next question (user clicks "Next")
  const advanceToNext = useCallback(() => {
    if (!pendingNext) return
    const event = pendingNext
    setCurrentNodeId(event.node_id)
    setQuestion(event.text)
    setBreadcrumb(event.breadcrumb || [])
    setNodeText(event.node_text || '')
    setCaseRefs(event.case_refs || [])
    setRuleRefs(event.rule_refs || [])
    setMode(event.mode || 'quiz')
    setFeedbackText('')
    setPendingNext(null)
    submitTimeRef.current = Date.now()
  }, [pendingNext])

  // Pause
  const handlePause = useCallback(async () => {
    if (!sessionId) return
    try {
      await fetch(`${API_URL}/api/v1/study/session/${sessionId}/pause`, {
        method: 'POST',
        headers: getAuthHeaders(),
      })
    } catch {
      // ignore
    }
    setSessionId(null)
    setActiveMindmapId(null)
  }, [sessionId, getAuthHeaders])

  // Delete mindmap
  const handleDelete = async (id: number) => {
    if (!confirm('Delete this mindmap and all progress?')) return
    try {
      await fetch(`${API_URL}/api/v1/study/mindmaps/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      setMindmaps(prev => prev.filter(m => m.id !== id))
    } catch {
      // ignore
    }
  }

  // Tree node click - jump to branch
  const handleNodeClick = useCallback((nodeId: string) => {
    // Just highlight for now; could be used to start a branch session
  }, [])

  // Auth loading
  if (authLoading) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="flex items-center justify-center h-[80vh]">
          <Loader2 className="w-6 h-6 animate-spin text-sage-600" />
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="flex items-center justify-center h-[80vh]">
          <div className="text-center">
            <p className="text-stone-600 mb-3">Sign in to use Study Sessions</p>
            <button
              onClick={() => router.push('/login')}
              className="px-4 py-2 bg-sage-600 text-white rounded-lg hover:bg-sage-700"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Active session view
  if (sessionId && activeMindmapId && !completed) {
    return (
      <div className="min-h-screen bg-cream flex flex-col">
        <Header />
        <DopamineFlash event={dopamineEvent} onDone={() => setDopamineEvent(null)} />

        {/* Top bar */}
        <div className="sticky top-0 z-40 bg-cream/80 backdrop-blur-sm border-b border-stone-200 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={handlePause} className="text-stone-500 hover:text-stone-700">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <span className="text-sm text-stone-500 truncate max-w-xs">
              {breadcrumb.join(' > ')}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {streak > 0 && (
              <span className="flex items-center gap-1 text-sm font-semibold text-orange-500">
                <Flame className="w-4 h-4" /> {streak}
              </span>
            )}
            <button
              onClick={handlePause}
              className="flex items-center gap-1 px-3 py-1 text-sm text-stone-500 hover:text-stone-700 border border-stone-300 rounded-lg"
            >
              <Pause className="w-4 h-4" /> Pause
            </button>
          </div>
        </div>

        {/* 3-column layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left sidebar - tree (hidden on mobile, toggle) */}
          <div className={`${showSidebar ? 'block' : 'hidden'} lg:block w-64 shrink-0 border-r border-stone-200 bg-white overflow-y-auto`}>
            <MindmapTree
              nodes={nodes}
              currentNodeId={currentNodeId}
              onNodeClick={handleNodeClick}
            />
          </div>

          {/* Center - quiz card */}
          <div className="flex-1 flex flex-col p-4 lg:p-6 overflow-y-auto">
            {error && (
              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
                <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
              </div>
            )}
            <QuizCard
              question={question}
              breadcrumb={breadcrumb}
              nodeText={nodeText}
              caseRefs={caseRefs}
              ruleRefs={ruleRefs}
              mode={mode}
              streaming={streaming}
              feedbackText={feedbackText}
              onSubmit={handleSubmit}
              onSkip={handleSkip}
              onNext={advanceToNext}
              nextReady={!!pendingNext}
            />
          </div>

          {/* Right sidebar - progress */}
          <div className="hidden lg:block w-56 shrink-0 border-l border-stone-200 bg-white p-4">
            <ProgressPanel
              streak={streak}
              maxStreak={maxStreak}
              nodesMastered={nodesMastered}
              totalNodes={totalNodes}
              totalCorrect={totalCorrect}
              totalIncorrect={totalIncorrect}
              mode={mode}
            />
          </div>
        </div>

        {/* Mobile toggle */}
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          className="lg:hidden fixed bottom-4 left-4 z-40 px-3 py-2 bg-sage-600 text-white rounded-full shadow-lg text-sm"
        >
          Topics
        </button>
      </div>
    )
  }

  // Completed view
  if (completed) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="max-w-md mx-auto mt-20 text-center p-6">
          <div className="text-5xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-stone-800 mb-2">All Nodes Mastered!</h2>
          <p className="text-stone-500 mb-6">Great work! You&apos;ve mastered every concept in this mindmap.</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => { setCompleted(false); setActiveMindmapId(null); setSessionId(null) }}
              className="px-4 py-2 bg-sage-600 text-white rounded-lg hover:bg-sage-700"
            >
              Back to Mindmaps
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Mindmap list / picker view
  return (
    <div className="min-h-screen bg-cream">
      <Header />
      {showUpload && (
        <MindmapUpload
          apiUrl={API_URL}
          getAuthHeaders={getAuthHeaders}
          onUploaded={(mm) => {
            setMindmaps(prev => [mm, ...prev])
            setShowUpload(false)
          }}
          onClose={() => setShowUpload(false)}
        />
      )}

      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-stone-800">Study Sessions</h1>
            <p className="text-sm text-stone-500 mt-1">Upload a mindmap and study node-by-node with active recall</p>
          </div>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-4 py-2 bg-sage-600 text-white rounded-lg hover:bg-sage-700 transition-colors"
          >
            <Upload className="w-4 h-4" /> Upload Mindmap
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-sage-600" />
          </div>
        ) : mindmaps.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border border-stone-200">
            <Upload className="w-10 h-10 text-stone-300 mx-auto mb-3" />
            <p className="text-stone-500">No mindmaps yet</p>
            <p className="text-sm text-stone-400 mt-1">Upload a .mindmap.json file to get started</p>
          </div>
        ) : (
          <div className="space-y-3">
            {mindmaps.map((mm) => (
              <div
                key={mm.id}
                className="bg-white rounded-xl border border-stone-200 p-4 flex items-center justify-between hover:border-sage-300 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-stone-800 truncate">{mm.name}</h3>
                  <div className="flex items-center gap-3 text-xs text-stone-400 mt-1">
                    <span>{mm.node_count} nodes</span>
                    <span>{mm.max_depth} levels</span>
                    <span>{mm.nodes_mastered}/{mm.node_count} mastered</span>
                  </div>
                  {mm.node_count > 0 && (
                    <div className="mt-2 h-1.5 w-40 bg-stone-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-sage-500 rounded-full"
                        style={{ width: `${Math.round((mm.nodes_mastered / mm.node_count) * 100)}%` }}
                      />
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => startSession(mm.id)}
                    className="px-4 py-2 bg-sage-600 text-white rounded-lg text-sm font-medium hover:bg-sage-700 transition-colors"
                  >
                    Study
                  </button>
                  <button
                    onClick={() => handleDelete(mm.id)}
                    className="p-2 text-stone-400 hover:text-red-500 transition-colors"
                    title="Delete mindmap"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
