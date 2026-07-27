'use client'

import { ReactNode } from 'react'
import { track } from '@/lib/analytics'

interface DonateLinkProps {
  href: string
  /** Which donate button this is, for donate_click attribution. */
  placement: string
  className?: string
  children: ReactNode
}

/**
 * Ko-fi link that reports donate_click. Exists so pages that are otherwise
 * server components (e.g. /byok, which exports metadata) can track the click
 * without being converted to client components wholesale.
 */
export default function DonateLink({ href, placement, className, children }: DonateLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => track('donate_click', { placement })}
      className={className}
    >
      {children}
    </a>
  )
}
