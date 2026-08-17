'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Header from '@/components/Header'
import MemoWorkbench from '@/components/memo/MemoWorkbench'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import { Loader2 } from 'lucide-react'
import type { ToolProject } from '@/types'

export default function MemoProjectPage() {
  const params = useParams()
  const router = useRouter()
  const { user, session } = useAuth()
  const [project, setProject] = useState<ToolProject | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const projectId = params.id as string

  const loadProject = useCallback(async () => {
    const token = session?.access_token
    if (!token) return
    try {
      const res = await fetch(`${API_URL}/api/v1/tools/memo/projects/${projectId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) { setProject(await res.json()); setError(null) }
      else if (res.status === 404) setError('Project not found.')
      else setError('Failed to load project.')
    } catch { setError('Failed to load project.') }
    finally { setLoading(false) }
  }, [projectId, session])

  useEffect(() => {
    if (user && session) loadProject()
    else if (user === null) { setLoading(false); router.push('/login') }
  }, [user, session, loadProject, router])

  return (
    <div className="min-h-screen bg-cream">
      <Header />
      {loading ? (
        <div className="flex items-center justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-sage-600" /></div>
      ) : error ? (
        <div className="container mx-auto px-4 py-12 max-w-2xl">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
        </div>
      ) : project ? (
        <MemoWorkbench project={project} onProjectUpdated={loadProject} />
      ) : null}
    </div>
  )
}
