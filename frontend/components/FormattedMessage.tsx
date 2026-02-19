import React from 'react'

function formatInline(text: string): React.ReactNode {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>
    }
    return <span key={i}>{part}</span>
  })
}

export function FormattedMessage({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <>
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith('### ')) {
          return <h4 key={i} className="font-semibold text-neutral-900 mt-3 mb-1">{line.slice(4)}</h4>
        }
        if (line.startsWith('## ')) {
          return <h3 key={i} className="font-bold text-neutral-900 mt-3 mb-1">{line.slice(3)}</h3>
        }
        if (line.startsWith('# ')) {
          return <h2 key={i} className="text-lg font-bold text-neutral-900 mt-3 mb-1">{line.slice(2)}</h2>
        }
        // Bullet points
        if (line.match(/^[-*]\s/)) {
          return <p key={i} className="ml-4 before:content-['\2022'] before:mr-2 before:text-neutral-400">{formatInline(line.slice(2))}</p>
        }
        // Numbered list
        if (line.match(/^\d+\.\s/)) {
          return <p key={i} className="ml-4">{formatInline(line)}</p>
        }
        // Empty line
        if (!line.trim()) {
          return <br key={i} />
        }
        // Regular text
        return <p key={i}>{formatInline(line)}</p>
      })}
    </>
  )
}
