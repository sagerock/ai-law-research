import { Metadata } from 'next'
import Header from '@/components/Header'
import CivProTimeline from './CivProTimeline'
import { Scale } from 'lucide-react'

export const metadata: Metadata = {
  title: "Civil Procedure Timeline | Sage's Study Group",
  description:
    'Interactive guide to the stages of civil litigation with FRCP rules and landmark cases. Follow a federal civil case from filing through enforcement.',
}

export default function CivProPage() {
  return (
    <div className="min-h-screen bg-cream">
      <Header />
      <main className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Scale className="h-6 w-6 text-sage-600" />
            <h1 className="font-display text-3xl sm:text-4xl text-stone-900">
              Civil Procedure Timeline
            </h1>
          </div>
          <p className="text-stone-600 text-lg">
            The life of a federal civil lawsuit — from pre-filing to enforcement
          </p>
        </div>
        <CivProTimeline />
      </main>
    </div>
  )
}
