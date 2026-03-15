'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ChevronDown, ChevronRight, Expand, Minimize2, AlertTriangle } from 'lucide-react'
import { stages, Stage, Branch } from './timelineData'

function getAccentColor(id: number) {
  if (id <= 4) return { border: 'border-l-sage-500', circle: 'bg-sage-500', text: 'text-sage-700' }
  if (id === 5) return { border: 'border-l-sage-600', circle: 'bg-sage-600', text: 'text-sage-700' }
  if (id === 6) return { border: 'border-l-amber-600', circle: 'bg-amber-600', text: 'text-amber-700' }
  if (id === 7) return { border: 'border-l-sage-700', circle: 'bg-sage-700', text: 'text-sage-800' }
  return { border: 'border-l-stone-500', circle: 'bg-stone-500', text: 'text-stone-700' }
}

function BranchPoint({ branch }: { branch: Branch }) {
  return (
    <div className="flex items-center gap-3 mt-4">
      <div className="w-12 border-t-2 border-dashed border-amber-300" />
      <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-sm">
        <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
        <div>
          <span className="font-semibold text-amber-800">{branch.label}</span>
          <p className="text-amber-700 text-xs mt-0.5">{branch.description}</p>
          <div className="flex flex-wrap gap-1 mt-1.5">
            {branch.rules.map((r) => (
              <span key={r} className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs rounded-full font-medium">
                {r}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function DiscoveryGrid({ tools }: { tools: { name: string; description: string }[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 mt-3">
      {tools.map((tool) => (
        <div key={tool.name} className="bg-sage-50 border border-sage-200 rounded-lg px-3 py-2.5">
          <div className="font-medium text-sage-800 text-sm">{tool.name}</div>
          <div className="text-sage-600 text-xs mt-0.5">{tool.description}</div>
        </div>
      ))}
    </div>
  )
}

function StageCard({ stage, expanded, onToggle }: { stage: Stage; expanded: boolean; onToggle: () => void }) {
  const accent = getAccentColor(stage.id)

  return (
    <div className="relative pl-12 sm:pl-16 pb-8">
      {/* Vertical line connecting stages */}
      {stage.id < stages.length && (
        <div className="absolute left-[17px] sm:left-[25px] top-10 bottom-0 w-0.5 bg-sage-200" />
      )}

      {/* Stage number circle */}
      <div className={`absolute left-1.5 sm:left-2.5 top-1 w-8 h-8 sm:w-10 sm:h-10 ${accent.circle} rounded-full flex items-center justify-center text-white font-bold text-sm sm:text-base shadow-md z-10`}>
        {stage.id}
      </div>

      {/* Card */}
      <div
        className={`bg-white rounded-xl border border-stone-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden border-l-4 ${accent.border} ${stage.isWide && expanded ? 'max-w-4xl' : 'max-w-2xl'}`}
      >
        {/* Card header — clickable */}
        <button
          onClick={onToggle}
          className="w-full text-left px-4 py-3.5 sm:px-5 sm:py-4 flex items-start gap-3 group"
        >
          <div className="flex-1 min-w-0">
            <h3 className={`font-display text-lg sm:text-xl ${accent.text} leading-tight`}>
              {stage.title}
            </h3>
            <p className="text-stone-500 text-sm mt-0.5">{stage.subtitle}</p>
            {!expanded && (
              <p className="text-stone-400 text-xs mt-1">
                {stage.rules.length} rule{stage.rules.length !== 1 ? 's' : ''}
                {stage.keyCases ? ` · ${stage.keyCases.length} key case${stage.keyCases.length !== 1 ? 's' : ''}` : ''}
              </p>
            )}
          </div>
          <div className="text-stone-400 group-hover:text-stone-600 transition-colors mt-1">
            {expanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
          </div>
        </button>

        {/* Expanded content */}
        {expanded && (
          <div className="px-4 pb-4 sm:px-5 sm:pb-5 border-t border-stone-100 pt-3">
            {/* Rules */}
            <div>
              <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">Rules</h4>
              <div className="flex flex-wrap gap-1.5">
                {stage.rules.map((r) =>
                  r.slug ? (
                    <Link
                      key={r.rule}
                      href={`/rules/${r.slug}`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-sage-50 text-sage-700 text-sm rounded-full hover:bg-sage-100 hover:text-sage-800 transition-colors border border-sage-200"
                      title={r.description}
                    >
                      {r.rule}
                    </Link>
                  ) : (
                    <span
                      key={r.rule}
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-stone-50 text-stone-600 text-sm rounded-full border border-stone-200"
                      title={r.description}
                    >
                      {r.rule}
                    </span>
                  )
                )}
              </div>

              {/* Rule descriptions */}
              <div className="mt-3 space-y-1">
                {stage.rules.map((r) => (
                  <div key={r.rule} className="flex gap-2 text-sm">
                    <span className="text-stone-400 font-mono text-xs mt-0.5 shrink-0 w-24 sm:w-28 text-right">{r.rule}</span>
                    <span className="text-stone-600">{r.description}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Discovery grid */}
            {stage.discoveryTools && (
              <div className="mt-4">
                <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">Discovery Tools</h4>
                <DiscoveryGrid tools={stage.discoveryTools} />
              </div>
            )}

            {/* Key cases */}
            {stage.keyCases && stage.keyCases.length > 0 && (
              <div className="mt-4">
                <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-2">Key Cases</h4>
                <ul className="space-y-1">
                  {stage.keyCases.map((c) => (
                    <li key={c} className="text-sm text-stone-600 italic">
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Branch points */}
            {stage.branches?.map((b) => (
              <BranchPoint key={b.label} branch={b} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function CivProTimeline() {
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set([1]))
  const allExpanded = expanded.size === stages.length

  function toggleStage(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (allExpanded) {
      setExpanded(new Set())
    } else {
      setExpanded(new Set(stages.map((s) => s.id)))
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <p className="text-stone-500 text-sm max-w-xl">
          Follow a civil case from pre-filing investigation through enforcement. Click any stage to explore the relevant FRCP rules and landmark cases.
        </p>
        <button
          onClick={toggleAll}
          className="flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-700 transition-colors px-3 py-1.5 rounded-lg hover:bg-stone-100 shrink-0 ml-4"
        >
          {allExpanded ? <Minimize2 className="h-4 w-4" /> : <Expand className="h-4 w-4" />}
          <span className="hidden sm:inline">{allExpanded ? 'Collapse All' : 'Expand All'}</span>
        </button>
      </div>

      <div className="relative">
        {/* Top of timeline spine */}
        <div className="absolute left-[17px] sm:left-[25px] top-0 w-0.5 h-8 bg-sage-200" />

        {stages.map((stage) => (
          <StageCard
            key={stage.id}
            stage={stage}
            expanded={expanded.has(stage.id)}
            onToggle={() => toggleStage(stage.id)}
          />
        ))}
      </div>
    </div>
  )
}
