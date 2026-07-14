'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { Brain, FileText } from 'lucide-react'
import Header from '@/components/Header'

// Outlines is the flagship study tool (Sage, 2026-07-14). Mindmaps stays
// reachable at /study/session (existing users' maps + public share links)
// but is deliberately not in the tab nav — its tab reappears only when
// someone is already there. New study features (hypos, flashcards) get a
// tab here when they ship.
const TABS = [
  { href: '/study/outlines', label: 'Outlines', icon: FileText, match: /^\/study\/outlines/ },
]

const HIDDEN_TABS = [
  { href: '/study/session', label: 'Mindmaps', icon: Brain, match: /^\/study\/session/ },
]

export default function StudyLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  // Show a hidden tab only while the visitor is on its page, so direct
  // links still render a sensible active tab without advertising it.
  const visibleTabs = [
    ...TABS,
    ...HIDDEN_TABS.filter(tab => tab.match.test(pathname)),
  ]

  return (
    <>
      <Header />
      <div className="border-b bg-white">
        <div className="container mx-auto px-4">
          <nav className="flex gap-1 -mb-px">
            {visibleTabs.map(tab => {
              const active = tab.match.test(pathname)
              const Icon = tab.icon
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                    active
                      ? 'border-sage-600 text-sage-700'
                      : 'border-transparent text-stone-500 hover:text-stone-700 hover:border-stone-300'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </Link>
              )
            })}
          </nav>
        </div>
      </div>
      {children}
    </>
  )
}
