'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import { Scale, GraduationCap, BookOpen, Library, ChevronDown, MessageCircle, Heart } from 'lucide-react'
import { UserMenu } from '@/components/auth/UserMenu'

export default function Header() {
  const [refDropdownOpen, setRefDropdownOpen] = useState(false)
  const refDropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (refDropdownRef.current && !refDropdownRef.current.contains(e.target as Node)) {
        setRefDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="border-b bg-cream/80 backdrop-blur-md sticky top-0 z-50 overflow-visible">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 bg-sage-700 rounded-xl flex items-center justify-center shadow-sm group-hover:bg-sage-600 transition-colors">
              <Scale className="h-[18px] w-[18px] text-white" />
            </div>
            <div className="hidden sm:block">
              <span className="font-display text-xl text-stone-900 leading-none">Law Study Group</span>
              <span className="text-[12px] text-stone-500 block mt-0.5 tracking-wide">Free Case Briefs for Law Students</span>
            </div>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2">
            <Link
              href="/study"
              className="px-3 py-2 text-sm text-stone-600 hover:text-stone-900 hover:bg-stone-100
                         rounded-lg transition-all flex items-center gap-1.5"
            >
              <GraduationCap className="h-4 w-4" />
              <span className="hidden sm:inline">Study</span>
            </Link>

            <Link
              href="/textbooks"
              className="px-3 py-2 text-sm text-stone-600 hover:text-stone-900 hover:bg-stone-100
                         rounded-lg transition-all flex items-center gap-1.5"
            >
              <Library className="h-4 w-4" />
              <span className="hidden sm:inline">Textbooks</span>
            </Link>

            <div className="relative" ref={refDropdownRef}>
              <button
                onClick={() => setRefDropdownOpen(!refDropdownOpen)}
                className="px-3 py-2 text-sm text-stone-600 hover:text-stone-900 hover:bg-stone-100
                                     rounded-lg transition-all flex items-center gap-1.5"
              >
                <BookOpen className="h-4 w-4" />
                <span className="hidden sm:inline">Reference</span>
                <ChevronDown className={`h-3 w-3 hidden sm:block transition-transform ${refDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              {refDropdownOpen && (
                <div className="absolute right-0 top-full mt-1 w-56 bg-white border border-stone-200
                                rounded-xl shadow-lg shadow-stone-200/50 z-50 py-1.5">
                  <Link href="/rules" onClick={() => setRefDropdownOpen(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-stone-700
                                                 hover:bg-sage-50 hover:text-sage-700 transition-colors">
                    Federal Rules (FRCP)
                  </Link>
                  <Link href="/constitution" onClick={() => setRefDropdownOpen(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-stone-700
                                                        hover:bg-sage-50 hover:text-sage-700 transition-colors">
                    U.S. Constitution
                  </Link>
                  <Link href="/statutes" onClick={() => setRefDropdownOpen(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm text-stone-700
                                                    hover:bg-sage-50 hover:text-sage-700 transition-colors">
                    Federal Statutes
                  </Link>
                </div>
              )}
            </div>

            <Link
              href="/transparency"
              className="px-3 py-2 text-sm text-stone-600 hover:text-stone-900 hover:bg-stone-100
                         rounded-lg transition-all flex items-center gap-1.5"
            >
              <Heart className="h-4 w-4" />
              <span className="hidden sm:inline">Contribute</span>
            </Link>

            <a
              href="https://discord.gg/AcGcKMmMZX"
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-2 text-stone-500 hover:text-stone-700 hover:bg-stone-100
                         rounded-lg transition-all"
              title="Discord"
            >
              <MessageCircle className="h-4 w-4" />
            </a>

            <div className="ml-1 pl-2 border-l border-stone-200">
              <UserMenu />
            </div>
          </nav>
        </div>
      </div>
    </header>
  )
}
