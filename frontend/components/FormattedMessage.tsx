import React from 'react'

function formatInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = []
  // Match **bold**, *italic*, or `code` — bold first to avoid conflict with italic
  const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g
  let last = 0
  let match: RegExpExecArray | null
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(<span key={`t${last}`}>{text.slice(last, match.index)}</span>)
    }
    if (match[2]) {
      parts.push(<strong key={`b${match.index}`} className="font-semibold">{match[2]}</strong>)
    } else if (match[3]) {
      parts.push(<em key={`i${match.index}`}>{match[3]}</em>)
    } else if (match[4]) {
      parts.push(
        <code key={`c${match.index}`} className="bg-neutral-200 text-neutral-800 px-1 py-0.5 rounded text-xs font-mono">
          {match[4]}
        </code>
      )
    }
    last = match.index + match[0].length
  }
  if (last < text.length) {
    parts.push(<span key={`t${last}`}>{text.slice(last)}</span>)
  }
  return parts.length > 0 ? parts : [<span key="full">{text}</span>]
}

export function FormattedMessage({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trimStart()
        // Headers
        if (trimmed.startsWith('### ')) {
          return <h4 key={i} className="font-semibold text-neutral-900 mt-3 mb-1">{formatInline(trimmed.slice(4))}</h4>
        }
        if (trimmed.startsWith('## ')) {
          return <h3 key={i} className="font-bold text-neutral-900 mt-3 mb-1">{formatInline(trimmed.slice(3))}</h3>
        }
        if (trimmed.startsWith('# ')) {
          return <h2 key={i} className="text-lg font-bold text-neutral-900 mt-3 mb-1">{formatInline(trimmed.slice(2))}</h2>
        }
        // Bullet points (- or * at start of line followed by space)
        if (trimmed.match(/^[-*]\s/)) {
          return (
            <div key={i} className="flex gap-2 ml-2">
              <span className="text-neutral-400 select-none">&bull;</span>
              <span>{formatInline(trimmed.slice(2))}</span>
            </div>
          )
        }
        // Numbered list
        if (trimmed.match(/^\d+\.\s/)) {
          return <p key={i} className="ml-2">{formatInline(trimmed)}</p>
        }
        // Empty line
        if (!trimmed) {
          return <div key={i} className="h-2" />
        }
        // Regular text
        return <p key={i}>{formatInline(trimmed)}</p>
      })}
    </div>
  )
}
