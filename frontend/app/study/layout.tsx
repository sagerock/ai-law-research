'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { MessageCircle, Brain, FileText } from 'lucide-react'

const TABS = [
  { href: '/study', label: 'Chat', icon: MessageCircle, match: /^\/study$/ },
  { href: '/study/session', label: 'Mindmaps', icon: Brain, match: /^\/study\/session/ },
  { href: '/study/outlines', label: 'Outlines', icon: FileText, match: /^\/study\/outlines/ },
]

export default function StudyLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <>
      <div className="border-b bg-white sticky top-[57px] z-40">
        <div className="container mx-auto px-4">
          <nav className="flex gap-1 -mb-px">
            {TABS.map(tab => {
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
