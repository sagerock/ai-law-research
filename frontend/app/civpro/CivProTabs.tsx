'use client'

import { useState } from 'react'
import { Map, ListOrdered, FileText } from 'lucide-react'
import CivProTimeline from './CivProTimeline'
import OutlineView from './OutlineView'
import { flowOutline, fullOutline } from './outlineData'

type Tab = 'timeline' | 'flow' | 'full'

const tabs: { id: Tab; label: string; icon: typeof Map; description: string }[] = [
  { id: 'timeline', label: 'Timeline', icon: Map, description: 'Interactive stages with rules and concepts' },
  { id: 'flow', label: 'Flow Outline', icon: ListOrdered, description: 'One-page procedural flow' },
  { id: 'full', label: 'Full Outline', icon: FileText, description: 'Complete topic-by-topic outline' },
]

export default function CivProTabs() {
  const [active, setActive] = useState<Tab>('timeline')

  return (
    <div>
      {/* Tab bar */}
      <div className="flex gap-1 mb-6 border-b border-stone-200">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = active === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                isActive
                  ? 'border-sage-600 text-sage-700'
                  : 'border-transparent text-stone-500 hover:text-stone-700 hover:border-stone-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.label.split(' ')[0]}</span>
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      {active === 'timeline' && <CivProTimeline />}
      {active === 'flow' && (
        <div>
          <p className="text-stone-500 text-sm mb-6 max-w-xl">
            A condensed view of the entire civil procedure process — every stage, every key rule, and when it fires.
          </p>
          <OutlineView markdown={flowOutline} />
        </div>
      )}
      {active === 'full' && (
        <div>
          <p className="text-stone-500 text-sm mb-6 max-w-xl">
            Complete outline organized by topic with all rules, standards, and distinctions from the mindmap.
          </p>
          <OutlineView markdown={fullOutline} />
        </div>
      )}
    </div>
  )
}
