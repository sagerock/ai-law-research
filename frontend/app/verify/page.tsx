'use client'

import CitationVerifier from '@/components/CitationVerifier'
import Header from '@/components/Header'

export default function VerifyPage() {
  return (
    <div className="min-h-screen bg-cream">
      <Header />
      <main className="container mx-auto px-4 py-8">
        <CitationVerifier />
      </main>
    </div>
  )
}
