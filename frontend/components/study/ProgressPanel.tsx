'use client'

import { Flame, Brain } from 'lucide-react'

interface ProgressPanelProps {
  streak: number
  maxStreak: number
  nodesMastered: number
  totalNodes: number
  totalCorrect: number
  totalIncorrect: number
  mode: string
}

export default function ProgressPanel({
  streak,
  maxStreak,
  nodesMastered,
  totalNodes,
  totalCorrect,
  totalIncorrect,
  mode,
}: ProgressPanelProps) {
  const pct = totalNodes > 0 ? Math.round((nodesMastered / totalNodes) * 100) : 0

  const modeLabels: Record<string, string> = {
    quiz: 'Quiz',
    story: 'Story',
    analogy: 'Analogy',
    hypo: 'Hypo',
    go_deeper: 'Deep Dive',
  }

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-stone-500 mb-1">
          <span>{pct}% mastered</span>
          <span>{nodesMastered}/{totalNodes}</span>
        </div>
        <div className="h-3 bg-stone-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-sage-600 rounded-full transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Streak */}
      <div className="flex items-center gap-2">
        <Flame className={`w-5 h-5 ${streak > 0 ? 'text-orange-500' : 'text-stone-300'}`} />
        <div>
          <div className="text-sm font-semibold">{streak} streak</div>
          <div className="text-xs text-stone-400">Best: {maxStreak}</div>
        </div>
      </div>

      {/* Score */}
      <div className="flex items-center gap-2">
        <Brain className="w-5 h-5 text-sage-600" />
        <div className="text-sm">
          <span className="text-green-600 font-medium">{totalCorrect}</span>
          {' / '}
          <span className="text-red-500 font-medium">{totalIncorrect}</span>
          <span className="text-stone-400 ml-1 text-xs">correct/wrong</span>
        </div>
      </div>

      {/* Mode */}
      <div className="text-xs text-stone-500">
        Mode: <span className="font-medium text-stone-700">{modeLabels[mode] || mode}</span>
      </div>
    </div>
  )
}
