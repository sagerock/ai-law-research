'use client'

import { Fragment, type ReactNode } from 'react'

interface OutlineViewProps {
  markdown: string
}

function parseLine(line: string) {
  // Detect indent level from leading spaces/dashes
  const stripped = line.replace(/^\s*-\s*/, '')
  const indent = line.match(/^(\s*)/)?.[1].length ?? 0
  const isBullet = line.trimStart().startsWith('-')
  const isH2 = line.startsWith('## ')
  const isH3 = line.startsWith('### ')

  return { stripped, indent, isBullet, isH2, isH3, raw: line }
}

function renderInline(text: string) {
  // Bold **text** and rule references
  const parts: (string | ReactNode)[] = []
  const regex = /\*\*([^*]+)\*\*/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    parts.push(
      <strong key={match.index} className="font-semibold text-stone-800">
        {match[1]}
      </strong>
    )
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }
  return parts
}

export default function OutlineView({ markdown }: OutlineViewProps) {
  const lines = markdown.split('\n')

  return (
    <div className="max-w-3xl">
      {lines.map((line, i) => {
        if (line.trim() === '') return <div key={i} className="h-3" />

        const { isH2, isH3, isBullet, raw } = parseLine(line)

        if (isH2) {
          return (
            <h2 key={i} className="text-lg font-display font-bold text-sage-700 mt-6 mb-2 pb-1 border-b border-sage-200">
              {renderInline(line.replace(/^##\s*/, ''))}
            </h2>
          )
        }

        if (isH3) {
          return (
            <h3 key={i} className="text-base font-semibold text-stone-700 mt-4 mb-1.5">
              {renderInline(line.replace(/^###\s*/, ''))}
            </h3>
          )
        }

        if (isBullet) {
          // Count leading spaces to determine nesting
          const leadingSpaces = raw.match(/^(\s*)/)?.[1].length ?? 0
          const depth = Math.floor(leadingSpaces / 2)
          const content = raw.replace(/^\s*-\s*/, '')

          return (
            <div
              key={i}
              className="flex gap-2 text-sm text-stone-600 leading-relaxed"
              style={{ paddingLeft: `${depth * 1.25 + 0.5}rem` }}
            >
              <span className="text-sage-400 mt-0.5 shrink-0">•</span>
              <span>{renderInline(content)}</span>
            </div>
          )
        }

        return (
          <p key={i} className="text-sm text-stone-600 leading-relaxed">
            {renderInline(line)}
          </p>
        )
      })}
    </div>
  )
}
