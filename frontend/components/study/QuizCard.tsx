'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, SkipForward, Loader2, ArrowRight } from 'lucide-react'
import { FormattedMessage } from '@/components/FormattedMessage'
import type { NodeRef } from '@/types'

interface QuizCardProps {
  question: string
  breadcrumb: string[]
  nodeText: string
  caseRefs: NodeRef[]
  ruleRefs: NodeRef[]
  mode: string
  streaming: boolean
  feedbackText: string
  onSubmit: (answer: string) => void
  onSkip: () => void
  onNext: () => void
  nextReady: boolean
}

export default function QuizCard({
  question,
  breadcrumb,
  nodeText,
  caseRefs,
  ruleRefs,
  mode,
  streaming,
  feedbackText,
  onSubmit,
  onSkip,
  onNext,
  nextReady,
}: QuizCardProps) {
  const [answer, setAnswer] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const submitStartRef = useRef<number>(0)

  useEffect(() => {
    if (!streaming) {
      textareaRef.current?.focus()
      submitStartRef.current = Date.now()
    }
  }, [question, streaming])

  const handleSubmit = useCallback(() => {
    if (!answer.trim() || streaming) return
    onSubmit(answer.trim())
    setAnswer('')
  }, [answer, streaming, onSubmit])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  const linkedCases = caseRefs.filter(r => r.case_id)
  const linkedRules = ruleRefs.filter(r => r.item_id)

  return (
    <div className="flex flex-col h-full">
      {/* Breadcrumb */}
      <div className="text-xs text-stone-400 mb-2 truncate">
        {breadcrumb.join(' > ')}
      </div>

      {/* Question */}
      <div className="bg-sage-50 border border-sage-200 rounded-lg p-4 mb-4">
        <div className="text-sm font-semibold text-sage-800 mb-1">
          {mode !== 'quiz' && (
            <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-sage-200 text-sage-700 mr-2 uppercase">
              {mode}
            </span>
          )}
          Question
        </div>
        <p className="text-stone-700">{question}</p>
      </div>

      {/* Answer input */}
      <div className="mb-3">
        <textarea
          ref={textareaRef}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your answer..."
          disabled={streaming}
          rows={3}
          className="w-full px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sage-400 focus:border-transparent resize-none disabled:opacity-50"
        />
        <div className="flex gap-2 mt-2">
          <button
            onClick={handleSubmit}
            disabled={!answer.trim() || streaming}
            className="flex items-center gap-1 px-4 py-2 bg-sage-600 text-white rounded-lg text-sm font-medium hover:bg-sage-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Submit
          </button>
          <button
            onClick={onSkip}
            disabled={streaming}
            className="flex items-center gap-1 px-3 py-2 text-stone-500 hover:text-stone-700 text-sm transition-colors disabled:opacity-50"
          >
            <SkipForward className="w-4 h-4" />
            Skip
          </button>
        </div>
      </div>

      {/* Feedback area */}
      {feedbackText && (
        <div className="flex-1 overflow-y-auto border-t border-stone-200 pt-3 mb-3">
          <div className="text-xs font-semibold text-stone-500 uppercase mb-1">Feedback</div>
          <div className="text-sm text-stone-700">
            <FormattedMessage content={feedbackText} />
          </div>
          {nextReady && (
            <button
              onClick={onNext}
              className="mt-4 flex items-center gap-2 px-5 py-2.5 bg-sage-600 text-white rounded-lg text-sm font-semibold hover:bg-sage-700 transition-colors"
            >
              Next <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      )}

      {/* Case & Rule reference chips */}
      {(linkedCases.length > 0 || linkedRules.length > 0) && (
        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-stone-100">
          {linkedCases.map((ref, i) => (
            <a
              key={`case-${i}`}
              href={`/case/${ref.case_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
            >
              📋 {ref.name}
            </a>
          ))}
          {linkedRules.map((ref, i) => (
            <a
              key={`rule-${i}`}
              href={`/rules#${ref.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
            >
              📜 Rule {ref.ref}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
