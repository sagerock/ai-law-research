'use client'

import BriefUpload from '@/components/BriefUpload'
import Link from 'next/link'
import { Scale, MessageCircle, GraduationCap } from 'lucide-react'
import { UserMenu } from '@/components/auth/UserMenu'

export default function BriefCheckPage() {
  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
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
            <nav className="flex items-center space-x-4 sm:space-x-6">
              <Link
                href="/study"
                className="text-stone-600 hover:text-stone-900 transition flex items-center"
              >
                <GraduationCap className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Study</span>
              </Link>
              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="text-stone-600 hover:text-stone-900 transition flex items-center"
                title="Discord"
              >
                <MessageCircle className="h-5 w-5" />
              </a>
              <UserMenu />
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <BriefUpload />
      </main>
    </div>
  )
}
