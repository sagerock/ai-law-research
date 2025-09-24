import BriefUpload from '@/components/BriefUpload'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export default function BriefCheckPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-neutral-100">
      {/* Header */}
      <header className="border-b bg-white">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link
              href="/"
              className="flex items-center text-neutral-600 hover:text-neutral-900"
            >
              <ArrowLeft className="h-5 w-5 mr-2" />
              Back to Search
            </Link>
            <h1 className="text-xl font-bold text-neutral-900">Legal Research Tool</h1>
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