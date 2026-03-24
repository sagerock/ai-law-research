'use client'

import { useState, useCallback } from 'react'
import { Upload, FileText, Loader2, Trash2, AlertCircle } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import type { MSJDocument } from '@/types'

interface MSJDocumentUploadProps {
  projectId: number
  step: number
  title: string
  description: string
  docTypes: string[]
  documents: MSJDocument[]
  allDocuments: MSJDocument[]
  onDocumentsChange: (docs: MSJDocument[]) => void
}

export default function MSJDocumentUpload({
  projectId,
  step,
  title,
  description,
  docTypes,
  documents,
  allDocuments,
  onDocumentsChange,
}: MSJDocumentUploadProps) {
  const { getAccessToken } = useAuth()
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDocType, setSelectedDocType] = useState(docTypes[0])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true)
    else if (e.type === 'dragleave') setDragActive(false)
  }, [])

  const uploadFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!ext || !['pdf', 'docx', 'txt'].includes(ext)) {
      setError('Only PDF, DOCX, and TXT files are supported')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File must be under 10MB')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const token = await getAccessToken()
      const formData = new FormData()
      formData.append('file', file)
      formData.append('doc_type', selectedDocType)
      formData.append('title', file.name.replace(/\.[^.]+$/, ''))
      formData.append('step', String(step))

      const res = await fetch(`${API_URL}/api/v1/msj/projects/${projectId}/documents`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Upload failed')
      }

      const newDoc = await res.json()
      // Merge into allDocuments
      onDocumentsChange([...allDocuments, newDoc])
    } catch (e: any) {
      setError(e.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)
      if (e.dataTransfer.files) {
        Array.from(e.dataTransfer.files).forEach(uploadFile)
      }
    },
    [selectedDocType]
  )

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      Array.from(e.target.files).forEach(uploadFile)
    }
  }

  const deleteDoc = async (docId: number) => {
    try {
      const token = await getAccessToken()
      await fetch(`${API_URL}/api/v1/msj/projects/${projectId}/documents/${docId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      onDocumentsChange(allDocuments.filter((d) => d.id !== docId))
    } catch (e) {
      setError('Failed to delete document')
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
          <Upload className="h-5 w-5 text-sage-700" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-stone-900">{title}</h2>
          <p className="text-sm text-stone-500">{description}</p>
        </div>
      </div>

      {docTypes.length > 1 && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-stone-700 mb-1">Document Type</label>
          <select
            value={selectedDocType}
            onChange={(e) => setSelectedDocType(e.target.value)}
            className="px-3 py-2 border border-stone-200 rounded-lg text-sm
                       focus:outline-none focus:ring-2 focus:ring-sage-500 focus:border-transparent"
          >
            {docTypes.map((t) => (
              <option key={t} value={t}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-center gap-2 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Upload area */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer mb-4 ${
          dragActive
            ? 'border-sage-400 bg-sage-50'
            : 'border-stone-200 hover:border-stone-300'
        }`}
        onClick={() => document.getElementById(`file-input-step-${step}`)?.click()}
      >
        <input
          id={`file-input-step-${step}`}
          type="file"
          accept=".pdf,.docx,.txt"
          multiple
          onChange={handleFileInput}
          className="hidden"
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="h-8 w-8 text-sage-600 animate-spin" />
            <p className="text-sm text-stone-500">Uploading and extracting text...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload className="h-8 w-8 text-stone-300" />
            <p className="text-sm text-stone-600">
              Drop files here or <span className="text-sage-700 font-medium">browse</span>
            </p>
            <p className="text-xs text-stone-400">PDF, DOCX, or TXT (max 10MB each)</p>
          </div>
        )}
      </div>

      {/* Uploaded documents list */}
      {documents.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-stone-700">
            Uploaded ({documents.length})
          </h3>
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 p-3 bg-stone-50 rounded-lg group"
            >
              <FileText className="h-5 w-5 text-stone-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-stone-700 truncate">{doc.title}</p>
                <p className="text-xs text-stone-400">
                  {doc.file_type?.toUpperCase()} &middot; {formatSize(doc.file_size)} &middot;{' '}
                  {doc.char_count.toLocaleString()} chars extracted
                </p>
              </div>
              <span className="text-xs px-2 py-0.5 bg-stone-200 text-stone-600 rounded-full">
                {doc.doc_type}
              </span>
              <button
                onClick={() => deleteDoc(doc.id)}
                className="p-1.5 text-stone-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
