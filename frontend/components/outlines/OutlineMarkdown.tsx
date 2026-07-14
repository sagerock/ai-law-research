import Link from 'next/link'
import type { ReactNode } from 'react'

const TOKEN = /(\*\*\[[^\]]+\]\([^)]+\)\*\*|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g

function renderLink(text: string, href: string, key: string): ReactNode {
  const className = "font-semibold text-honey-700 underline decoration-honey-300 decoration-2 underline-offset-2 hover:text-honey-600"
  return href.startsWith('/') ? (
    <Link key={key} href={href} className={className}>{text}</Link>
  ) : (
    <a key={key} href={href} className={className} rel="noopener noreferrer" target="_blank">{text}</a>
  )
}

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let cursor = 0

  for (const match of text.matchAll(TOKEN)) {
    const token = match[0]
    const index = match.index ?? 0
    if (index > cursor) nodes.push(text.slice(cursor, index))

    const strongLink = token.match(/^\*\*\[([^\]]+)\]\(([^)]+)\)\*\*$/)
    const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (strongLink) {
      nodes.push(renderLink(strongLink[1], strongLink[2], `${index}-${token}`))
    } else if (link) {
      nodes.push(renderLink(link[1], link[2], `${index}-${token}`))
    } else {
      nodes.push(<strong key={`${index}-${token}`} className="font-semibold text-stone-900">{token.slice(2, -2)}</strong>)
    }
    cursor = index + token.length
  }

  if (cursor < text.length) nodes.push(text.slice(cursor))
  return nodes
}

export default function OutlineMarkdown({ markdown }: { markdown: string }) {
  const lines = markdown.split('\n')
  const blocks: ReactNode[] = []

  for (let index = 0; index < lines.length;) {
    const line = lines[index]
    if (!line.trim()) {
      index += 1
      continue
    }
    if (line.startsWith('### ')) {
      blocks.push(
        <h3 key={index} className="mt-7 mb-3 text-lg font-semibold text-sage-900">
          {renderInline(line.slice(4))}
        </h3>
      )
      index += 1
      continue
    }
    if (line.startsWith('- ')) {
      const items: ReactNode[] = []
      while (index < lines.length && (lines[index].startsWith('- ') || lines[index].startsWith('  - '))) {
        const parent = lines[index].slice(2)
        const children: ReactNode[] = []
        index += 1
        while (index < lines.length && lines[index].startsWith('  - ')) {
          children.push(<li key={index}>{renderInline(lines[index].slice(4))}</li>)
          index += 1
        }
        items.push(
          <li key={`item-${index}`}>
            {renderInline(parent)}
            {children.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-stone-600">{children}</ul>}
          </li>
        )
      }
      blocks.push(<ul key={`list-${index}`} className="list-disc space-y-2.5 pl-5 text-[15px] leading-7 text-stone-700">{items}</ul>)
      continue
    }

    blocks.push(<p key={index} className="text-[15px] leading-7 text-stone-600">{renderInline(line)}</p>)
    index += 1
  }

  return <div>{blocks}</div>
}
