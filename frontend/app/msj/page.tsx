'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Header from '@/components/Header'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import { FileText, Plus, Loader2, Trash2, AlertCircle } from 'lucide-react'
import type { MSJProject } from '@/types'

export default function MSJPage() {
  const { user, session } = useAuth()
  const router = useRouter()
  const [projects, setProjects] = useState<MSJProject[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user) loadProjects()
    else setLoading(false)
  }, [user])

  const loadProjects = async (retries = 2) => {
    try {
      const token = session?.access_token
      if (!token) {
        // Token not ready yet — retry after a short delay
        if (retries > 0) {
          setTimeout(() => loadProjects(retries - 1), 2000)
          return
        }
        setError('Unable to load motions — please refresh the page.')
        setLoading(false)
        return
      }
      const res = await fetch(`${API_URL}/api/v1/msj/projects`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        setProjects(await res.json())
        setError(null)
      } else if (res.status === 401 && retries > 0) {
        // Token may have just expired — retry once
        setTimeout(() => loadProjects(retries - 1), 2000)
        return
      } else {
        setError('Failed to load motions. Please try refreshing.')
      }
    } catch (e) {
      console.error('Failed to load projects:', e)
      setError('Failed to load motions.')
    } finally {
      setLoading(false)
    }
  }

  const createProject = async () => {
    setCreating(true)
    setError(null)
    try {
      const token = session?.access_token
      if (!token) {
        setError('Session expired. Please sign in again.')
        return
      }
      const res = await fetch(`${API_URL}/api/v1/msj/projects`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      })
      if (res.ok) {
        const project = await res.json()
        router.push(`/msj/${project.id}`)
      } else {
        setError('Failed to create project. Please try again.')
      }
    } catch (e) {
      setError('Failed to create project')
    } finally {
      setCreating(false)
    }
  }

  const deleteProject = async (id: number) => {
    if (!confirm('Delete this project and all its documents?')) return
    try {
      const token = session?.access_token
      await fetch(`${API_URL}/api/v1/msj/projects/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      setProjects(projects.filter((p) => p.id !== id))
    } catch (e) {
      setError('Failed to delete project')
    }
  }

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: 'bg-stone-100 text-stone-600',
      generating: 'bg-amber-100 text-amber-700',
      complete: 'bg-sage-100 text-sage-700',
    }
    return (
      <span className={`text-xs px-2 py-0.5 rounded-full ${styles[status] || styles.draft}`}>
        {status}
      </span>
    )
  }

  return (
    <div className="min-h-screen bg-cream">
      <Header />
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-display text-stone-900">Motion for Summary Judgment</h1>
            <p className="text-sm text-stone-500 mt-1">
              Build practice MSJ motions with AI assistance using your uploaded documents
            </p>
          </div>
          {user && (
            <button
              onClick={createProject}
              disabled={creating}
              className="flex items-center gap-2 px-4 py-2 bg-sage-700 text-white rounded-lg
                         hover:bg-sage-600 transition-colors disabled:opacity-50 text-sm"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              New Motion
            </button>
          )}
        </div>

        {/* Educational disclaimer */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex gap-2">
            <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800">Educational Tool Only</p>
              <p className="text-xs text-amber-700 mt-1">
                This tool generates practice motions for law students. Output should not be filed
                with any court. All AI-generated content uses only your uploaded documents and
                approved legal resources — no hallucinated citations.
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {!user ? (
          <div className="bg-white rounded-xl border border-stone-200 p-12 text-center">
            <FileText className="h-12 w-12 text-stone-300 mx-auto mb-4" />
            <h2 className="text-lg font-medium text-stone-700 mb-2">Sign in to get started</h2>
            <p className="text-sm text-stone-500 mb-4">
              Create an account to build and save your practice motions.
            </p>
            <button
              onClick={() => router.push('/login')}
              className="px-4 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 transition-colors text-sm"
            >
              Sign In
            </button>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-sage-600" />
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-white rounded-xl border border-stone-200 p-12 text-center">
            <FileText className="h-12 w-12 text-stone-300 mx-auto mb-4" />
            <h2 className="text-lg font-medium text-stone-700 mb-2">No motions yet</h2>
            <p className="text-sm text-stone-500 mb-4">
              Create your first Motion for Summary Judgment to get started.
            </p>
            <button
              onClick={createProject}
              disabled={creating}
              className="px-4 py-2 bg-sage-700 text-white rounded-lg hover:bg-sage-600 transition-colors text-sm"
            >
              Create Motion
            </button>
          </div>
        ) : (
          <div className="grid gap-3">
            {projects.map((project) => {
              const caseInfo = project.case_info || {}
              const hasParties = caseInfo.plaintiff || caseInfo.defendant
              return (
                <div
                  key={project.id}
                  className="bg-white rounded-xl border border-stone-200 p-4 hover:border-sage-300
                             transition-colors cursor-pointer group"
                  onClick={() => router.push(`/msj/${project.id}`)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-stone-900 truncate">
                          {hasParties
                            ? `${caseInfo.plaintiff || '?'} v. ${caseInfo.defendant || '?'}`
                            : project.title}
                        </h3>
                        {statusBadge(project.status)}
                      </div>
                      <p className="text-xs text-stone-500">
                        {project.doc_count || 0} documents &middot; Updated{' '}
                        {new Date(project.updated_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteProject(project.id)
                      }}
                      className="p-2 text-stone-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                      title="Delete project"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
