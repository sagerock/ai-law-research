'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Header from '@/components/Header'
import AffidavitWizard from '@/components/affidavit/AffidavitWizard'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import { Loader2 } from 'lucide-react'
import type { ToolProject } from '@/types'

export default function AffidavitProjectPage() {
  const params = useParams()
  const router = useRouter()
  const { user, session } = useAuth()
  const [project, setProject] = useState<ToolProject | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const projectId = params.id as string

  useEffect(() => {
    if (user) loadProject()
  }, [user, projectId])

  const loadProject = async () => {
    try {
      const token = session?.access_token
      const res = await fetch(`${API_URL}/api/v1/tools/affidavit/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 404) { setError('Project not found'); return }
      if (!res.ok) throw new Error('Failed to load project')
      setProject(await res.json())
    } catch { setError('Failed to load project') }
    finally { setLoading(false) }
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="flex items-center justify-center py-16">
          <p className="text-stone-500">Please sign in to access your projects.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-sage-600" />
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-cream">
        <Header />
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <p className="text-stone-500">{error || 'Project not found'}</p>
          <button onClick={() => router.push('/tools/affidavit')} className="text-sm text-sage-700 hover:underline">
            Back to affidavits
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream">
      <Header />
      <AffidavitWizard project={project} onUpdate={setProject} />
    </div>
  )
}
