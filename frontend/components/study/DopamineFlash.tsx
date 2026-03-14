'use client'

import { useEffect, useState } from 'react'

interface DopamineFlashProps {
  event: string | null
  onDone: () => void
}

export default function DopamineFlash({ event, onDone }: DopamineFlashProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!event) return
    setVisible(true)
    const timer = setTimeout(() => {
      setVisible(false)
      onDone()
    }, 1800)
    return () => clearTimeout(timer)
  }, [event, onDone])

  if (!visible || !event) return null

  const config: Record<string, { emoji: string; text: string; color: string }> = {
    mastered: { emoji: '✅', text: 'Node Mastered!', color: 'from-green-500/20 to-transparent' },
    streak_5: { emoji: '🔥', text: '5 Streak!', color: 'from-orange-500/20 to-transparent' },
    streak_10: { emoji: '🔥🔥', text: '10 Streak!', color: 'from-red-500/20 to-transparent' },
    streak_25: { emoji: '💎', text: '25 Streak!', color: 'from-purple-500/20 to-transparent' },
    streak_50: { emoji: '👑', text: '50 Streak!', color: 'from-yellow-500/20 to-transparent' },
  }

  const c = config[event] || config.mastered

  return (
    <div className="fixed inset-0 z-50 pointer-events-none flex items-center justify-center">
      <div
        className={`bg-gradient-radial ${c.color} animate-dopamine-flash rounded-full w-64 h-64 flex flex-col items-center justify-center`}
      >
        <span className="text-5xl animate-dopamine-bounce">{c.emoji}</span>
        <span className="text-lg font-bold text-stone-800 mt-2 animate-fade-in">{c.text}</span>
      </div>
      <style jsx>{`
        @keyframes dopamine-flash {
          0% { opacity: 0; transform: scale(0.5); }
          30% { opacity: 1; transform: scale(1.1); }
          70% { opacity: 1; transform: scale(1); }
          100% { opacity: 0; transform: scale(1.2); }
        }
        @keyframes dopamine-bounce {
          0% { transform: scale(0); }
          40% { transform: scale(1.3); }
          60% { transform: scale(0.9); }
          80% { transform: scale(1.05); }
          100% { transform: scale(1); }
        }
        .animate-dopamine-flash {
          animation: dopamine-flash 1.8s ease-out forwards;
        }
        .animate-dopamine-bounce {
          animation: dopamine-bounce 0.6s ease-out 0.1s forwards;
        }
      `}</style>
    </div>
  )
}
