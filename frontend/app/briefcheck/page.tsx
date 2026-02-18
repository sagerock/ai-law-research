'use client'

import BriefUpload from '@/components/BriefUpload'
import Link from 'next/link'
import { Scale, Upload, Heart, BookOpen, MessageCircle, GraduationCap } from 'lucide-react'
import { UserMenu } from '@/components/auth/UserMenu'

export default function BriefCheckPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-neutral-100">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50 overflow-visible">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="flex items-center space-x-3">
              <Scale className="h-8 w-8 text-neutral-700" />
              <div>
                <h1 className="text-2xl font-bold text-neutral-900">Law Study Group</h1>
                <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
              </div>
            </Link>
            <nav className="flex items-center space-x-4 sm:space-x-6">
              <Link
                href="/briefcheck"
                className="text-neutral-900 font-medium flex items-center"
              >
                <Upload className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Brief Check</span>
              </Link>
              <Link
                href="/transparency"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <Heart className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Transparency</span>
              </Link>
              <Link
                href="/library"
                className="text-neutral-600 hover:text-neutral-900 transition hidden sm:flex items-center"
              >
                <BookOpen className="h-5 w-5 mr-2" />
                My Library
              </Link>
              <Link
                href="/study"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <GraduationCap className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Study</span>
              </Link>
              <a
                href="https://discord.gg/AcGcKMmMZX"
                target="_blank"
                rel="noopener noreferrer"
                className="text-neutral-600 hover:text-neutral-900 transition flex items-center"
              >
                <MessageCircle className="h-5 w-5 sm:mr-2" />
                <span className="hidden sm:inline">Discord</span>
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
