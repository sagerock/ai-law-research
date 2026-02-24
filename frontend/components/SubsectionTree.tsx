'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, Copy, Check } from 'lucide-react'

interface Subsection {
  label?: string
  text?: string
  title?: string
  id?: string
  subsections?: Subsection[]
  sections?: Subsection[]
}

interface SubsectionTreeProps {
  items: Subsection[]
  depth?: number
  defaultExpanded?: boolean
}

function SubsectionNode({ item, depth = 0, defaultExpanded = false }: {
  item: Subsection
  depth: number
  defaultExpanded: boolean
}) {
  const children = item.subsections || item.sections || []
  const hasChildren = children.length > 0
  const [expanded, setExpanded] = useState(defaultExpanded || depth < 1)
  const [copied, setCopied] = useState(false)

  const label = item.label || item.title || ''
  const text = item.text || ''

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    const fullText = `${label} ${text}`.trim()
    navigator.clipboard.writeText(fullText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  // Indent based on depth
  const indentClass = depth === 0 ? '' : depth === 1 ? 'ml-4' : depth === 2 ? 'ml-8' : 'ml-12'

  return (
    <div className={indentClass}>
      <div
        className={`group flex items-start gap-2 py-1.5 ${hasChildren ? 'cursor-pointer' : ''}`}
        onClick={hasChildren ? () => setExpanded(!expanded) : undefined}
      >
        {hasChildren ? (
          <button className="mt-0.5 flex-shrink-0 text-neutral-400 hover:text-neutral-600">
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ) : (
          <span className="w-4 flex-shrink-0" />
        )}

        <div className="flex-1 min-w-0">
          <p className="text-neutral-800 leading-relaxed">
            {label && (
              <span className="font-semibold text-neutral-900">{label} </span>
            )}
            {text}
          </p>
        </div>

        <button
          onClick={handleCopy}
          className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity
                     text-neutral-400 hover:text-neutral-600 mt-0.5"
          title="Copy text"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {hasChildren && expanded && (
        <div className="border-l border-neutral-200 ml-2">
          {children.map((child, i) => (
            <SubsectionNode
              key={child.id || child.label || i}
              item={child}
              depth={depth + 1}
              defaultExpanded={defaultExpanded}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function SubsectionTree({ items, depth = 0, defaultExpanded = false }: SubsectionTreeProps) {
  if (!items || items.length === 0) return null

  return (
    <div className="space-y-0.5">
      {items.map((item, i) => (
        <SubsectionNode
          key={item.id || item.label || i}
          item={item}
          depth={depth}
          defaultExpanded={defaultExpanded}
        />
      ))}
    </div>
  )
}
