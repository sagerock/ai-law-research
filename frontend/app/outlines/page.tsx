'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import { createClient } from '@/lib/supabase'
import { API_URL } from '@/lib/api'
import { Outline } from '@/types'
import { UserMenu } from '@/components/auth/UserMenu'
import {
  Scale,
  FileText,
  Upload,
  Heart,
  BookOpen,
  MessageCircle,
  Loader2,
  Download,
  Trash2,
  X,
  Plus,
  Filter,
} from 'lucide-react'

const SUBJECT_OPTIONS = [
  'Constitutional Law',
  'Contracts',
  'Civil Procedure',
  'Criminal Law',
  'Criminal Procedure',
  'Evidence',
  'Property',
  'Torts',
  'Administrative Law',
  'Business Associations',
  'Family Law',
  'Immigration Law',
  'Intellectual Property',
  'International Law',
  'Labor Law',
  'Legal Writing',
  'Professional Responsibility',
  'Remedies',
  'Securities Regulation',
  'Tax Law',
  'Trusts & Estates',
]

interface SubjectCount {
  subject: string
  count: number
}

export default function OutlinesPage() {
  const { user, session, isLoading: authLoading } = useAuth()
  const [mounted, setMounted] = useState(false)

  // Browse state
  const [outlines, setOutlines] = useState<Outline[]>([])
  const [myOutlines, setMyOutlines] = useState<Outline[]>([])
  const [subjects, setSubjects] = useState<SubjectCount[]>([])
  const [subjectFilter, setSubjectFilter] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadSubject, setUploadSubject] = useState('')
  const [uploadProfessor, setUploadProfessor] = useState('')
  const [uploadLawSchool, setUploadLawSchool] = useState('')
  const [uploadSemester, setUploadSemester] = useState('')
  const [uploadDescription, setUploadDescription] = useState('')
  const [uploadPublic, setUploadPublic] = useState(true)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  // Delete state
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const getAuthHeaders = (): Record<string, string> => {
    if (!session?.access_token) return {}
    return {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json'
    }
  }

  const fetchOutlines = useCallback(async (subject?: string) => {
    try {
      const params = new URLSearchParams()
      if (subject) params.set('subject', subject)
      const res = await fetch(`${API_URL}/api/v1/outlines?${params}`)
      const data = await res.json()
      setOutlines(data.outlines || [])
    } catch (err) {
      console.error('Failed to fetch outlines:', err)
    }
  }, [])

  const fetchSubjects = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/subjects`)
      const data = await res.json()
      setSubjects(data.subjects || [])
    } catch (err) {
      console.error('Failed to fetch subjects:', err)
    }
  }, [])

  const fetchMyOutlines = useCallback(async () => {
    if (!session?.access_token) return
    try {
      const res = await fetch(`${API_URL}/api/v1/outlines/mine`, {
        headers: { 'Authorization': `Bearer ${session.access_token}` }
      })
      const data = await res.json()
      setMyOutlines(data.outlines || [])
    } catch (err) {
      console.error('Failed to fetch my outlines:', err)
    }
  }, [session?.access_token])

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return

    const loadData = async () => {
      setIsLoading(true)
      await Promise.all([
        fetchOutlines(),
        fetchSubjects(),
        ...(session?.access_token ? [fetchMyOutlines()] : [])
      ])
      setIsLoading(false)
    }

    loadData()
  }, [mounted, session?.access_token, fetchOutlines, fetchSubjects, fetchMyOutlines])

  // Filter change
  useEffect(() => {
    if (mounted) {
      fetchOutlines(subjectFilter || undefined)
    }
  }, [subjectFilter, mounted, fetchOutlines])

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleFileSelect = (file: File) => {
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    const validExts = ['.pdf', '.docx']
    const isValid = validTypes.includes(file.type) || validExts.some(ext => file.name.toLowerCase().endsWith(ext))

    if (!isValid) {
      setUploadError('Please upload a PDF or DOCX file')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File size must be under 10MB')
      return
    }

    setUploadFile(file)
    setUploadError(null)

    // Auto-fill title from filename if empty
    if (!uploadTitle) {
      const name = file.name.replace(/\.(pdf|docx)$/i, '').replace(/[_-]/g, ' ')
      setUploadTitle(name)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile || !uploadTitle.trim() || !uploadSubject.trim() || !user || !session?.access_token) return

    setIsUploading(true)
    setUploadError(null)

    try {
      // 1. Upload file to Supabase Storage
      const supabase = createClient()
      if (!supabase) {
        throw new Error('Supabase not configured')
      }

      const path = `${user.id}/${Date.now()}_${uploadFile.name}`
      const { error: storageError } = await supabase.storage.from('outlines').upload(path, uploadFile)
      if (storageError) throw new Error(`Upload failed: ${storageError.message}`)

      const { data: urlData } = supabase.storage.from('outlines').getPublicUrl(path)
      const fileUrl = urlData.publicUrl

      // 2. Save metadata to backend
      const fileType = uploadFile.name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'docx'
      const res = await fetch(`${API_URL}/api/v1/outlines`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          title: uploadTitle.trim(),
          subject: uploadSubject.trim(),
          professor: uploadProfessor.trim() || null,
          law_school: uploadLawSchool.trim() || null,
          semester: uploadSemester.trim() || null,
          description: uploadDescription.trim() || null,
          filename: uploadFile.name,
          file_url: fileUrl,
          file_size: uploadFile.size,
          file_type: fileType,
          is_public: uploadPublic,
        }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || 'Failed to save outline')
      }

      // 3. Success - close modal & refresh
      setShowUploadModal(false)
      resetUploadForm()
      await Promise.all([fetchOutlines(subjectFilter || undefined), fetchSubjects(), fetchMyOutlines()])
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const resetUploadForm = () => {
    setUploadTitle('')
    setUploadSubject('')
    setUploadProfessor('')
    setUploadLawSchool('')
    setUploadSemester('')
    setUploadDescription('')
    setUploadPublic(true)
    setUploadFile(null)
    setUploadError(null)
  }

  const handleDelete = async (outlineId: number, fileUrl: string) => {
    if (!session?.access_token) return
    setDeletingId(outlineId)

    try {
      // Delete from backend
      const res = await fetch(`${API_URL}/api/v1/outlines/${outlineId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${session.access_token}` },
      })
      if (!res.ok) throw new Error('Delete failed')

      // Try to delete from Supabase Storage
      const supabase = createClient()
      if (supabase && fileUrl) {
        // Extract path from URL: .../object/public/outlines/{path}
        const match = fileUrl.match(/\/outlines\/(.+)$/)
        if (match) {
          await supabase.storage.from('outlines').remove([match[1]])
        }
      }

      // Refresh
      await Promise.all([fetchOutlines(subjectFilter || undefined), fetchSubjects(), fetchMyOutlines()])
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setDeletingId(null)
    }
  }

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  // Nav component shared between states
  const Nav = ({ active = false }: { active?: boolean }) => (
    <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50 overflow-visible">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center space-x-3">
            <Scale className="h-8 w-8 text-neutral-700" />
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">Sage&apos;s Law School Study Group</h1>
              <p className="text-sm text-neutral-600 hidden sm:block">Free AI Case Briefs for Law Students</p>
            </div>
          </Link>
          <nav className="flex items-center space-x-4 sm:space-x-6">
            <Link href="/briefcheck" className="text-neutral-600 hover:text-neutral-900 transition flex items-center">
              <Upload className="h-5 w-5 sm:mr-2" />
              <span className="hidden sm:inline">Brief Check</span>
            </Link>
            <Link href="/transparency" className="text-neutral-600 hover:text-neutral-900 transition flex items-center">
              <Heart className="h-5 w-5 sm:mr-2" />
              <span className="hidden sm:inline">Transparency</span>
            </Link>
            <Link href="/library" className="text-neutral-600 hover:text-neutral-900 transition hidden sm:flex items-center">
              <BookOpen className="h-5 w-5 mr-2" />
              My Library
            </Link>
            <Link href="/outlines" className="text-neutral-900 font-medium transition flex items-center">
              <FileText className="h-5 w-5 sm:mr-2" />
              <span className="hidden sm:inline">Outlines</span>
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
  )

  if (!mounted || isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
        <Nav />
        <div className="flex items-center justify-center py-32">
          <Loader2 className="h-8 w-8 animate-spin text-neutral-400" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-neutral-50 to-white">
      <Nav />

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h2 className="text-3xl font-bold text-neutral-900">Community Outlines</h2>
            <p className="text-neutral-600 mt-1">Share and download law school outlines from fellow students</p>
          </div>
          {user && (
            <button
              onClick={() => setShowUploadModal(true)}
              className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
            >
              <Plus className="h-5 w-5 mr-2" />
              Upload Outline
            </button>
          )}
          {!user && !authLoading && (
            <Link
              href="/login"
              className="inline-flex items-center px-5 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
            >
              Sign in to upload
            </Link>
          )}
        </div>

        {/* Subject Filter */}
        {subjects.length > 0 && (
          <div className="flex items-center gap-3 mb-6 flex-wrap">
            <Filter className="h-4 w-4 text-neutral-500" />
            <button
              onClick={() => setSubjectFilter('')}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
                !subjectFilter ? 'bg-blue-600 text-white' : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
              }`}
            >
              All ({subjects.reduce((sum, s) => sum + s.count, 0)})
            </button>
            {subjects.map(s => (
              <button
                key={s.subject}
                onClick={() => setSubjectFilter(s.subject === subjectFilter ? '' : s.subject)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
                  subjectFilter === s.subject ? 'bg-blue-600 text-white' : 'bg-neutral-100 text-neutral-700 hover:bg-neutral-200'
                }`}
              >
                {s.subject} ({s.count})
              </button>
            ))}
          </div>
        )}

        {/* Outlines Grid */}
        {outlines.length === 0 ? (
          <div className="text-center py-20">
            <FileText className="h-16 w-16 text-neutral-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-neutral-700 mb-2">No outlines yet</h3>
            <p className="text-neutral-500">
              {user ? 'Be the first to upload an outline!' : 'Sign in to upload the first outline.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-12">
            {outlines.map(outline => (
              <div key={outline.id} className="bg-white rounded-lg border hover:shadow-md transition p-5">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-neutral-900 line-clamp-2">{outline.title}</h3>
                  <span className="ml-2 flex-shrink-0 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                    {outline.file_type?.toUpperCase() || 'PDF'}
                  </span>
                </div>

                <span className="inline-block px-2.5 py-1 bg-purple-100 text-purple-700 text-xs font-medium rounded-full mb-3">
                  {outline.subject}
                </span>

                {outline.description && (
                  <p className="text-sm text-neutral-600 line-clamp-2 mb-3">{outline.description}</p>
                )}

                <div className="space-y-1 text-sm text-neutral-500 mb-4">
                  {outline.professor && <div>Prof. {outline.professor}</div>}
                  {outline.law_school && <div>{outline.law_school}</div>}
                  {outline.semester && <div>{outline.semester}</div>}
                </div>

                <div className="flex items-center justify-between text-xs text-neutral-400 pt-3 border-t">
                  <div className="flex items-center gap-3">
                    <span>{outline.username || outline.full_name || 'Anonymous'}</span>
                    <span>{outline.created_at ? formatDate(outline.created_at) : ''}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {outline.file_size && <span>{formatFileSize(outline.file_size)}</span>}
                    <span className="flex items-center">
                      <Download className="h-3 w-3 mr-1" />
                      {outline.download_count}
                    </span>
                  </div>
                </div>

                <a
                  href={outline.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 w-full inline-flex items-center justify-center px-4 py-2 bg-neutral-100 text-neutral-700 rounded-lg text-sm font-medium hover:bg-neutral-200 transition"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </a>
              </div>
            ))}
          </div>
        )}

        {/* My Outlines Section */}
        {user && myOutlines.length > 0 && (
          <div className="mt-12">
            <h3 className="text-xl font-bold text-neutral-900 mb-4">My Outlines</h3>
            <div className="space-y-3">
              {myOutlines.map(outline => (
                <div key={outline.id} className="bg-white rounded-lg border p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4 min-w-0">
                    <FileText className="h-8 w-8 text-blue-500 flex-shrink-0" />
                    <div className="min-w-0">
                      <div className="font-medium text-neutral-900 truncate">{outline.title}</div>
                      <div className="text-sm text-neutral-500 flex items-center gap-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">
                          {outline.subject}
                        </span>
                        {!outline.is_public && (
                          <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs rounded-full">Private</span>
                        )}
                        <span>{outline.download_count} downloads</span>
                        {outline.created_at && <span>{formatDate(outline.created_at)}</span>}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(outline.id, outline.file_url)}
                    disabled={deletingId === outline.id}
                    className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition flex-shrink-0"
                    title="Delete outline"
                  >
                    {deletingId === outline.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-neutral-900">Upload Outline</h3>
              <button
                onClick={() => { setShowUploadModal(false); resetUploadForm() }}
                className="p-1 hover:bg-neutral-100 rounded-lg transition"
              >
                <X className="h-5 w-5 text-neutral-500" />
              </button>
            </div>

            <div className="space-y-4">
              {/* File Drop Zone */}
              <div
                className={`relative border-2 border-dashed rounded-lg p-6 text-center transition ${
                  dragActive ? 'border-blue-400 bg-blue-50' : uploadFile ? 'border-green-300 bg-green-50' : 'border-neutral-300'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  id="outline-file"
                  className="hidden"
                  accept=".pdf,.docx"
                  onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                />
                {uploadFile ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <FileText className="h-5 w-5 text-green-600 mr-3" />
                      <div className="text-left">
                        <div className="font-medium text-neutral-700">{uploadFile.name}</div>
                        <div className="text-sm text-neutral-500">{formatFileSize(uploadFile.size)}</div>
                      </div>
                    </div>
                    <button onClick={() => setUploadFile(null)} className="text-red-500 hover:text-red-600 text-sm">
                      Remove
                    </button>
                  </div>
                ) : (
                  <label htmlFor="outline-file" className="cursor-pointer">
                    <Upload className="h-10 w-10 text-neutral-400 mx-auto mb-2" />
                    <p className="font-medium text-neutral-700">Drop your outline here or click to browse</p>
                    <p className="text-sm text-neutral-500 mt-1">PDF or DOCX, max 10MB</p>
                  </label>
                )}
              </div>

              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Title *</label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="e.g. Con Law Final Outline"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              {/* Subject */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Subject *</label>
                <select
                  value={uploadSubject}
                  onChange={(e) => setUploadSubject(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none bg-white"
                >
                  <option value="">Select a subject...</option>
                  {SUBJECT_OPTIONS.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {/* Professor & Law School */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Professor</label>
                  <input
                    type="text"
                    value={uploadProfessor}
                    onChange={(e) => setUploadProfessor(e.target.value)}
                    placeholder="Professor name"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">Law School</label>
                  <input
                    type="text"
                    value={uploadLawSchool}
                    onChange={(e) => setUploadLawSchool(e.target.value)}
                    placeholder="e.g. Harvard Law"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
              </div>

              {/* Semester */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Semester</label>
                <input
                  type="text"
                  value={uploadSemester}
                  onChange={(e) => setUploadSemester(e.target.value)}
                  placeholder="e.g. Fall 2025"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">Description</label>
                <textarea
                  value={uploadDescription}
                  onChange={(e) => setUploadDescription(e.target.value)}
                  placeholder="Brief description of your outline..."
                  rows={2}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
                />
              </div>

              {/* Public Toggle */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="outline-public"
                  checked={uploadPublic}
                  onChange={(e) => setUploadPublic(e.target.checked)}
                  className="h-4 w-4 text-blue-600 rounded"
                />
                <label htmlFor="outline-public" className="text-sm text-neutral-700">
                  Make this outline public (visible to everyone)
                </label>
              </div>

              {/* Error */}
              {uploadError && (
                <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg">{uploadError}</div>
              )}

              {/* Submit */}
              <button
                onClick={handleUpload}
                disabled={isUploading || !uploadFile || !uploadTitle.trim() || !uploadSubject.trim()}
                className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-neutral-300 disabled:cursor-not-allowed transition flex items-center justify-center"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin mr-2" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="h-5 w-5 mr-2" />
                    Upload Outline
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
