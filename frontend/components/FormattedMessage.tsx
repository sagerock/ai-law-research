import React from 'react'
import Link from 'next/link'
import { parseLegalCitations } from '@/lib/legalCitations'

// Case names ("Anderson v. Liberty Lobby") and "Id." should be italicized per Bluebook
const LEGAL_ITALIC_RE = /(\b[A-Z][A-Za-z'.]+(?:\s+(?:of|for|the|and|in|ex|re)\s+[A-Z][A-Za-z'.]+)*(?:\s+[A-Z][A-Za-z'.]+)*(?:,?\s+(?:Inc|Corp|Co|Ltd|LLC)\.?)?\s+v\.?\s+[A-Z][A-Za-z'.]+(?:\s+(?:of|for|the|and|in|ex|re)\s+[A-Z][A-Za-z'.]+)*(?:\s+[A-Z][A-Za-z'.]+)*(?:,?\s+(?:Inc|Corp|Co|Ltd|LLC)\.?)?|\bId\.(?!\w))/g

function applyLegalItalics(text: string, keyPrefix: string, startIdx: number): [React.ReactNode[], number] {
  const parts: React.ReactNode[] = []
  let idx = startIdx
  let pos = 0
  LEGAL_ITALIC_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = LEGAL_ITALIC_RE.exec(text)) !== null) {
    if (m.index > pos) {
      parts.push(<span key={`${keyPrefix}${idx++}`}>{text.slice(pos, m.index)}</span>)
    }
    parts.push(<em key={`${keyPrefix}${idx++}`}>{m[0]}</em>)
    pos = m.index + m[0].length
  }
  if (pos < text.length) {
    parts.push(<span key={`${keyPrefix}${idx++}`}>{text.slice(pos)}</span>)
  }
  return [parts, idx]
}

function formatInline(text: string): React.ReactNode[] {
  // First, detect legal citations and split into segments
  const segments = parseLegalCitations(text)

  const parts: React.ReactNode[] = []
  let keyIdx = 0

  for (const segment of segments) {
    if (segment.href) {
      // Citation link
      parts.push(
        <Link
          key={`cite${keyIdx++}`}
          href={segment.href}
          className="text-sage-700 hover:text-sage-900 underline decoration-sage-300 hover:decoration-sage-500"
        >
          {segment.text}
        </Link>
      )
    } else {
      // Process bold/italic/code within non-link text
      const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g
      let last = 0
      let match: RegExpExecArray | null
      const src = segment.text
      while ((match = re.exec(src)) !== null) {
        if (match.index > last) {
          // Apply legal italics (case names, Id.) to plain text
          const [italicParts, newIdx] = applyLegalItalics(src.slice(last, match.index), 'li', keyIdx)
          parts.push(...italicParts)
          keyIdx = newIdx
        }
        if (match[2]) {
          parts.push(<strong key={`b${keyIdx++}`} className="font-semibold">{match[2]}</strong>)
        } else if (match[3]) {
          parts.push(<em key={`i${keyIdx++}`}>{match[3]}</em>)
        } else if (match[4]) {
          parts.push(
            <code key={`c${keyIdx++}`} className="bg-stone-200 text-stone-800 px-1 py-0.5 rounded text-xs font-mono">
              {match[4]}
            </code>
          )
        }
        last = match.index + match[0].length
      }
      if (last < src.length) {
        const [italicParts, newIdx] = applyLegalItalics(src.slice(last), 'li', keyIdx)
        parts.push(...italicParts)
        keyIdx = newIdx
      }
    }
  }

  return parts.length > 0 ? parts : [<span key="full">{text}</span>]
}

export function FormattedMessage({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const trimmed = line.trimStart()
        // Headers (check longest prefix first)
        if (trimmed.startsWith('#### ')) {
          return <h5 key={i} className="font-semibold text-stone-800 mt-2 mb-1">{formatInline(trimmed.slice(5))}</h5>
        }
        if (trimmed.startsWith('### ')) {
          return <h4 key={i} className="font-semibold text-stone-900 mt-3 mb-1">{formatInline(trimmed.slice(4))}</h4>
        }
        if (trimmed.startsWith('## ')) {
          return <h3 key={i} className="font-bold text-stone-900 mt-3 mb-1">{formatInline(trimmed.slice(3))}</h3>
        }
        if (trimmed.startsWith('# ')) {
          return <h2 key={i} className="text-lg font-bold text-stone-900 mt-3 mb-1">{formatInline(trimmed.slice(2))}</h2>
        }
        // Bullet points (- or * at start of line followed by space)
        if (trimmed.match(/^[-*]\s/)) {
          return (
            <div key={i} className="flex gap-2 ml-2">
              <span className="text-stone-400 select-none">&bull;</span>
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
