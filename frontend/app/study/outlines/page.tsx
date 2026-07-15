'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ArrowRight, BookOpen, FileText, Loader2, Plus, Trash2, Upload, X } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import { createClient } from '@/lib/supabase'
import type { Outline } from '@/types'

interface CanonicalOutlineSummary {
  slug: string
  title: string
  description: string
  section_count: number
}

const CANONICAL_FALLBACK: CanonicalOutlineSummary[] = [
  {
    slug: 'civil-procedure',
    title: 'The Civil Procedure Outline',
    description: 'A community-improved, source-linked guide to the federal civil litigation process.',
    section_count: 15,
  },
]

const SUBJECT_OPTIONS = [
  'Constitutional Law', 'Contracts', 'Civil Procedure', 'Criminal Law',
  'Criminal Procedure', 'Evidence', 'Property', 'Torts',
  'Administrative Law', 'Business Associations', 'Family Law',
  'Immigration Law', 'Intellectual Property', 'International Law',
  'Labor Law', 'Legal Writing', 'Professional Responsibility', 'Remedies',
  'Securities Regulation', 'Tax Law', 'Trusts & Estates',
]

export default function OutlinesPage() {
  const { user, session, isLoading: authLoading } = useAuth()
  const pathname = usePathname()
  const [myOutlines, setMyOutlines] = useState<Outline[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadSubject, setUploadSubject] = useState('')
  const [uploadDescription, setUploadDescription] = useState('')
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [canonicalOutlines, setCanonicalOutlines] = useState<CanonicalOutlineSummary[]>(CANONICAL_FALLBACK)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_URL}/api/v1/canonical-outlines`)
      .then(response => {
        if (!response.ok) throw new Error('Failed to load canonical outlines')
        return response.json()
      })
      .then(data => {
        if (!cancelled && Array.isArray(data.outlines) && data.outlines.length > 0) {
          setCanonicalOutlines(data.outlines)
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (authLoading) return
    if (!session?.access_token) {
      setMyOutlines([])
      setIsLoading(false)
      return
    }
    let cancelled = false
    setIsLoading(true)
    fetch(`${API_URL}/api/v1/outlines/mine`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    }).then(async response => {
      if (!response.ok) throw new Error('Failed to load outlines')
      const data = await response.json()
      if (!cancelled) setMyOutlines(data.outlines || [])
    }).catch(() => {
      if (!cancelled) setMyOutlines([])
    }).finally(() => {
      if (!cancelled) setIsLoading(false)
    })
    return () => { cancelled = true }
  }, [authLoading, session?.access_token])

  const resetUpload = () => {
    setUploadFile(null)
    setUploadTitle('')
    setUploadSubject('')
    setUploadDescription('')
    setUploadError(null)
  }

  const selectFile = (file: File) => {
    const valid = ['pdf', 'docx', 'txt'].includes(file.name.split('.').pop()?.toLowerCase() || '')
    if (!valid) {
      setUploadError('Please upload a PDF, DOCX, or TXT file')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File size must be under 10MB')
      return
    }
    setUploadFile(file)
    setUploadError(null)
    if (!uploadTitle) setUploadTitle(file.name.replace(/\.(pdf|docx|txt)$/i, '').replace(/[_-]/g, ' '))
  }

  const upload = async () => {
    if (!uploadFile || !uploadTitle.trim() || !uploadSubject || !session?.access_token) return
    setIsUploading(true)
    setUploadError(null)
    try {
      const form = new FormData()
      form.append('file', uploadFile)
      form.append('title', uploadTitle.trim())
      form.append('subject', uploadSubject)
      form.append('description', uploadDescription.trim())
      form.append('visibility', 'private')
      const response = await fetch(`${API_URL}/api/v1/outlines/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
        body: form,
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Upload failed')
      }
      const created = await response.json()
      setMyOutlines(current => [{
        ...created,
        description: uploadDescription.trim() || null,
        filename: uploadFile.name,
        file_url: '',
        file_size: uploadFile.size,
        file_type: uploadFile.name.split('.').pop() || null,
        professor: null,
        law_school: null,
        semester: null,
        year: null,
        fork_count: 0,
        forked_from: null,
      }, ...current])
      setShowUpload(false)
      resetUpload()
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const remove = async (outline: Outline) => {
    if (!session?.access_token) return
    setDeletingId(outline.id)
    try {
      const response = await fetch(`${API_URL}/api/v1/outlines/${outline.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      if (!response.ok) return
      if (outline.file_url) {
        const storagePath = outline.file_url.match(/\/outlines\/(.+)$/)?.[1]
        const supabase = createClient()
        if (storagePath && supabase) await supabase.storage.from('outlines').remove([storagePath])
      }
      setMyOutlines(current => current.filter(item => item.id !== outline.id))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <main className="min-h-[70vh] bg-cream">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-8">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-sage-700">Study tools</p>
          <h1 className="font-display text-4xl font-semibold text-stone-900 sm:text-5xl">Outlines</h1>
          <p className="mt-3 max-w-2xl text-stone-600">Start with Tortwell&apos;s source-linked canonical outlines, or privately upload your own outline to study against it with AI.</p>
        </header>

        <section className="mb-12 space-y-6">
          {canonicalOutlines.map(outline => (
            <div key={outline.slug} className="overflow-hidden rounded-3xl border border-sage-200 bg-white shadow-sm">
              <div className="grid md:grid-cols-[1fr_280px]">
                <div className="p-7 sm:p-9">
                  <span className="inline-flex rounded-full bg-sage-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-sage-700">Canonical outline</span>
                  <h2 className="mt-5 font-display text-3xl font-semibold text-stone-900 sm:text-4xl">{outline.title}</h2>
                  <p className="mt-3 max-w-2xl leading-7 text-stone-600">{outline.description}</p>
                  <div className="mt-6 flex flex-wrap gap-4 text-sm text-stone-500">
                    <span>{outline.section_count} sections</span><span>Source-linked rules and cases</span><span>Community feedback by section</span>
                  </div>
                  <Link href={`/outlines/${outline.slug}`} className="mt-7 inline-flex items-center gap-2 rounded-xl bg-sage-700 px-5 py-3 font-semibold text-white hover:bg-sage-600">
                    Open the outline <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
                <div className="flex min-h-52 items-center justify-center bg-sage-50 p-8">
                  <div className="flex h-36 w-36 items-center justify-center rounded-full border border-sage-200 bg-white shadow-sm">
                    <BookOpen className="h-16 w-16 text-sage-600" strokeWidth={1.4} />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </section>

        <section>
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-2xl font-semibold text-stone-900">My private outlines</h2>
              <p className="mt-1 text-sm text-stone-500">Your uploads are private and never enter the public outline.</p>
            </div>
            {user && <button onClick={() => setShowUpload(true)} className="inline-flex items-center gap-2 rounded-lg bg-sage-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sage-600"><Plus className="h-4 w-4" /> Upload</button>}
          </div>

          {authLoading || isLoading ? (
            <div className="rounded-2xl border border-stone-200 bg-white py-14"><Loader2 className="mx-auto h-6 w-6 animate-spin text-stone-400" /></div>
          ) : !user ? (
            <div className="rounded-2xl border border-stone-200 bg-white p-8 text-center">
              <FileText className="mx-auto mb-3 h-10 w-10 text-stone-300" />
              <p className="text-stone-600">Sign in to upload a private outline and use the AI study modes.</p>
              <Link href={`/login?returnTo=${encodeURIComponent(pathname)}`} className="mt-4 inline-flex rounded-lg bg-sage-700 px-4 py-2 text-sm font-semibold text-white">Sign in</Link>
            </div>
          ) : myOutlines.length === 0 ? (
            <button onClick={() => setShowUpload(true)} className="w-full rounded-2xl border-2 border-dashed border-stone-200 bg-white p-10 text-center hover:border-sage-300 hover:bg-sage-50/50">
              <Upload className="mx-auto mb-3 h-9 w-9 text-sage-500" />
              <span className="block font-semibold text-stone-800">Upload your first private outline</span>
              <span className="mt-1 block text-sm text-stone-500">PDF, DOCX, or TXT up to 10MB</span>
            </button>
          ) : (
            <div className="space-y-3">
              {myOutlines.map(outline => (
                <div key={outline.id} className="flex items-center gap-4 rounded-xl border border-stone-200 bg-white p-4">
                  <Link href={`/outline/${outline.id}`} className="flex min-w-0 flex-1 items-center gap-4 hover:opacity-80">
                    <FileText className="h-8 w-8 shrink-0 text-sage-500" />
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-stone-900">{outline.title}</p>
                      <p className="mt-1 text-sm text-stone-500">{outline.subject} · Private</p>
                    </div>
                  </Link>
                  <button onClick={() => remove(outline)} disabled={deletingId === outline.id} className="rounded-lg p-2 text-stone-400 hover:bg-red-50 hover:text-red-600" aria-label="Delete outline">
                    {deletingId === outline.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-6 flex items-center justify-between">
              <div><h2 className="text-xl font-bold text-stone-900">Upload a private outline</h2><p className="mt-1 text-sm text-stone-500">Only you can view and study this file.</p></div>
              <button onClick={() => { setShowUpload(false); resetUpload() }} className="rounded-lg p-1.5 hover:bg-stone-100"><X className="h-5 w-5" /></button>
            </div>
            <div className="space-y-4">
              <label className="block cursor-pointer rounded-xl border-2 border-dashed border-stone-200 p-6 text-center hover:border-sage-300">
                <input type="file" className="hidden" accept=".pdf,.docx,.txt" onChange={event => event.target.files?.[0] && selectFile(event.target.files[0])} />
                <Upload className="mx-auto mb-2 h-8 w-8 text-stone-400" />
                <span className="block font-medium text-stone-700">{uploadFile?.name || 'Choose a PDF, DOCX, or TXT file'}</span>
                <span className="mt-1 block text-xs text-stone-500">Maximum 10MB</span>
              </label>
              <div><label className="mb-1 block text-sm font-medium text-stone-700">Title</label><input value={uploadTitle} onChange={event => setUploadTitle(event.target.value)} className="w-full rounded-lg border px-3 py-2 outline-none focus:border-sage-500 focus:ring-2 focus:ring-sage-100" /></div>
              <div><label className="mb-1 block text-sm font-medium text-stone-700">Subject</label><select value={uploadSubject} onChange={event => setUploadSubject(event.target.value)} className="w-full rounded-lg border bg-white px-3 py-2 outline-none focus:border-sage-500"><option value="">Select a subject...</option>{SUBJECT_OPTIONS.map(subject => <option key={subject}>{subject}</option>)}</select></div>
              <div><label className="mb-1 block text-sm font-medium text-stone-700">Description <span className="font-normal text-stone-400">optional</span></label><textarea value={uploadDescription} onChange={event => setUploadDescription(event.target.value)} rows={2} className="w-full resize-none rounded-lg border px-3 py-2 outline-none focus:border-sage-500" /></div>
              {uploadError && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{uploadError}</p>}
              <button onClick={upload} disabled={isUploading || !uploadFile || !uploadTitle.trim() || !uploadSubject} className="flex w-full items-center justify-center gap-2 rounded-lg bg-sage-700 py-2.5 font-semibold text-white hover:bg-sage-600 disabled:bg-stone-300">
                {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Upload className="h-5 w-5" />} Upload privately
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
