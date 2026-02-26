'use client'

import BriefUpload from '@/components/BriefUpload'
import Header from '@/components/Header'

export default function BriefCheckPage() {
  return (
    <div className="min-h-screen bg-cream">
      <Header />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <BriefUpload />
      </main>
    </div>
  )
}
