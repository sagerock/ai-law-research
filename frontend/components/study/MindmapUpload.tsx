'use client'

import { useState, useRef, useCallback } from 'react'
import { Upload, X, FileText, Loader2 } from 'lucide-react'
import type { Mindmap } from '@/types'

interface MindmapUploadProps {
  apiUrl: string
  getAuthHeaders: () => Record<string, string>
  onUploaded: (mindmap: Mindmap) => void
  onClose: () => void
}

export default function MindmapUpload({ apiUrl, getAuthHeaders, onUploaded, onClose }: MindmapUploadProps) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Mindmap | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const upload = useCallback(async (file: File) => {
    setError(null)
    setUploading(true)

    try {
      const form = new FormData()
      form.append('file', file)

      const headers = getAuthHeaders()
      delete headers['Content-Type'] // let browser set multipart boundary

      const res = await fetch(`${apiUrl}/api/v1/study/mindmaps/upload`, {
        method: 'POST',
        headers,
        body: form,
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(body.detail || 'Upload failed')
      }

      const data = await res.json()
      setResult(data)
      onUploaded(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }, [apiUrl, getAuthHeaders, onUploaded])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) upload(file)
  }, [upload])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) upload(file)
  }, [upload])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-stone-800">Upload Mindmap</h3>
          <button onClick={onClose} className="text-stone-400 hover:text-stone-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {result ? (
          <div className="text-center py-4">
            <FileText className="w-10 h-10 text-sage-600 mx-auto mb-2" />
            <p className="font-semibold text-stone-800">{result.name}</p>
            <p className="text-sm text-stone-500 mt-1">
              {result.node_count} nodes &middot; {result.max_depth} levels deep
            </p>
            <button
              onClick={onClose}
              className="mt-4 px-4 py-2 bg-sage-600 text-white rounded-lg hover:bg-sage-700 transition-colors"
            >
              Start Studying
            </button>
          </div>
        ) : (
          <>
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragging ? 'border-sage-500 bg-sage-50' : 'border-stone-300'
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              {uploading ? (
                <Loader2 className="w-8 h-8 text-sage-600 animate-spin mx-auto" />
              ) : (
                <>
                  <Upload className="w-8 h-8 text-stone-400 mx-auto mb-2" />
                  <p className="text-sm text-stone-600">
                    Drag & drop a <span className="font-mono text-sage-700">.mindmap.json</span> file
                  </p>
                  <p className="text-xs text-stone-400 mt-1">or</p>
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="mt-2 text-sm text-sage-600 hover:text-sage-800 font-medium"
                  >
                    Browse files
                  </button>
                </>
              )}
              <input
                ref={fileRef}
                type="file"
                accept=".json,.mindmap.json"
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>
            {error && (
              <p className="mt-3 text-sm text-red-600">{error}</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
