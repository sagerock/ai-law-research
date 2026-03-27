'use client'

import { useRouter } from 'next/navigation'
import Header from '@/components/Header'
import { FileText, Scale, ArrowRight } from 'lucide-react'

const TOOLS = [
  {
    name: 'MSJ Builder',
    description: 'Build practice Motions for Summary Judgment with AI assistance',
    icon: FileText,
    href: '/msj',
    status: 'available' as const,
  },
  {
    name: 'Affidavit Builder',
    description: 'Draft affidavits with personal knowledge verification and proper formatting',
    icon: Scale,
    href: '/tools/affidavit',
    status: 'available' as const,
  },
]

export default function ToolsPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen bg-cream">
      <Header />
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-2xl font-display text-stone-900">Legal Document Tools</h1>
          <p className="text-sm text-stone-500 mt-1">
            AI-powered tools to help you practice drafting legal documents
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {TOOLS.map((tool) => {
            const Icon = tool.icon
            return (
              <button
                key={tool.name}
                onClick={() => router.push(tool.href)}
                className="bg-white rounded-xl border border-stone-200 p-6 text-left
                           hover:border-sage-300 hover:shadow-sm transition-all group"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-sage-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Icon className="h-6 w-6 text-sage-700" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h2 className="font-medium text-stone-900">{tool.name}</h2>
                      <ArrowRight className="h-4 w-4 text-stone-400 group-hover:text-sage-600 transition-colors" />
                    </div>
                    <p className="text-sm text-stone-500 mt-1">{tool.description}</p>
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        <div className="mt-8 bg-stone-50 rounded-xl border border-stone-200 p-6 text-center">
          <p className="text-sm text-stone-500">
            More tools coming soon: Legal Memo, Complaint, Answer, Motion in Limine, and more.
          </p>
        </div>
      </main>
    </div>
  )
}
