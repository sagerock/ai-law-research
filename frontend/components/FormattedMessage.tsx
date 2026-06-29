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

// Apply legal citation links + legal italics (case names, Id.) to a run of
// plain text that contains no markdown emphasis markers.
function linkAndItalicize(text: string, keyPrefix: string, startIdx: number): [React.ReactNode[], number] {
  const segments = parseLegalCitations(text)
  const parts: React.ReactNode[] = []
  let keyIdx = startIdx

  for (const segment of segments) {
    if (segment.href) {
      parts.push(
        <Link
          key={`${keyPrefix}cite${keyIdx++}`}
          href={segment.href}
          className="text-sage-700 hover:text-sage-900 underline decoration-sage-300 hover:decoration-sage-500"
        >
          {segment.text}
        </Link>
      )
    } else {
      const [italicParts, newIdx] = applyLegalItalics(segment.text, `${keyPrefix}li`, keyIdx)
      parts.push(...italicParts)
      keyIdx = newIdx
    }
  }

  return [parts, keyIdx]
}

function formatInline(text: string): React.ReactNode[] {
  // Parse markdown emphasis (bold/italic/code) FIRST so that emphasis markers
  // are never split by citation detection. Citation links and legal italics are
  // then applied within each plain-text run (and inside bold/italic content).
  const parts: React.ReactNode[] = []
  let keyIdx = 0

  const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g
  let last = 0
  let match: RegExpExecArray | null
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      const [linked, newIdx] = linkAndItalicize(text.slice(last, match.index), 'p', keyIdx)
      parts.push(...linked)
      keyIdx = newIdx
    }
    if (match[2] !== undefined) {
      const [inner, newIdx] = linkAndItalicize(match[2], 'b', keyIdx)
      keyIdx = newIdx
      parts.push(<strong key={`bold${keyIdx++}`} className="font-semibold">{inner}</strong>)
    } else if (match[3] !== undefined) {
      const [inner, newIdx] = linkAndItalicize(match[3], 'i', keyIdx)
      keyIdx = newIdx
      parts.push(<em key={`em${keyIdx++}`}>{inner}</em>)
    } else if (match[4] !== undefined) {
      parts.push(
        <code key={`code${keyIdx++}`} className="bg-stone-200 text-stone-800 px-1 py-0.5 rounded text-xs font-mono">
          {match[4]}
        </code>
      )
    }
    last = match.index + match[0].length
  }
  if (last < text.length) {
    const [linked, newIdx] = linkAndItalicize(text.slice(last), 'p', keyIdx)
    parts.push(...linked)
    keyIdx = newIdx
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
