'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { X, Save, Loader2, Play } from 'lucide-react'

interface MindmapEditorProps {
  apiUrl: string
  getAuthHeaders: () => Record<string, string>
  mindmapId?: number | null
  initialData?: any  // MindmapJSON tree
  onSave: (id: number) => void
  onClose: () => void
}

export default function MindmapEditor({
  apiUrl, getAuthHeaders, mindmapId, initialData, onSave, onClose
}: MindmapEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<any>(null)
  const [name, setName] = useState(initialData?.name || 'New Mind Map')
  const [saving, setSaving] = useState(false)
  const [savedId, setSavedId] = useState<number | null>(mindmapId || null)
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load mindmapper module on mount
  useEffect(() => {
    if (!containerRef.current) return

    // @ts-ignore - dynamic import of static JS module in /public
    import(/* webpackIgnore: true */ '/mindmapper-module.js').then((mod: any) => {
      const editor = mod.initMindmapper(containerRef.current!, {
        onDirty: () => setDirty(true),
      })
      editorRef.current = editor

      if (initialData) {
        try {
          editor.loadMap(initialData)
          setName(initialData.name || initialData.root?.text || 'New Mind Map')
        } catch (e: any) {
          setError('Failed to load mindmap: ' + e.message)
        }
      } else if (mindmapId) {
        // Load existing mindmap tree from API
        fetch(`${apiUrl}/api/v1/study/mindmaps/${mindmapId}`, { headers: getAuthHeaders() })
          .then(r => r.ok ? r.json() : Promise.reject(new Error('Failed to load')))
          .then(data => {
            if (data.tree) {
              editor.loadMap(typeof data.tree === 'string' ? JSON.parse(data.tree) : data.tree)
              setName(data.name || 'Mind Map')
            }
          })
          .catch(e => setError(e.message))
      }

      // Focus container for keyboard shortcuts
      containerRef.current!.focus()
    }).catch(e => {
      setError('Failed to load editor module: ' + e.message)
    })

    return () => {
      if (editorRef.current) editorRef.current.destroy()
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [])

  // Debounced auto-save when dirty
  useEffect(() => {
    if (!dirty || !savedId) return
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => doSave(true), 3000)
    return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current) }
  }, [dirty, savedId])

  const doSave = useCallback(async (silent = false) => {
    if (!editorRef.current) return
    const tree = editorRef.current.getTree()
    if (!tree) return

    if (!silent) setSaving(true)
    setError(null)

    try {
      const mapName = name.trim() || tree.name || 'Mind Map'
      if (savedId) {
        // Update existing
        const res = await fetch(`${apiUrl}/api/v1/study/mindmaps/${savedId}`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({ name: mapName, tree }),
        })
        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: 'Save failed' }))
          throw new Error(body.detail)
        }
        setDirty(false)
        if (!silent) onSave(savedId)
      } else {
        // Create new via upload-like endpoint - send as JSON body
        const res = await fetch(`${apiUrl}/api/v1/study/mindmaps/save`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ name: mapName, tree }),
        })
        if (!res.ok) {
          const body = await res.json().catch(() => ({ detail: 'Save failed' }))
          throw new Error(body.detail)
        }
        const data = await res.json()
        setSavedId(data.id)
        setDirty(false)
        if (!silent) onSave(data.id)
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      if (!silent) setSaving(false)
    }
  }, [name, savedId, apiUrl, getAuthHeaders, onSave])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Let the mindmapper container handle Tab/Enter/Delete etc.
    // Only intercept Ctrl+S for save
    if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      doSave()
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-cream flex flex-col"
      onKeyDown={handleKeyDown}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-stone-200 shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <button
            onClick={onClose}
            className="text-stone-400 hover:text-stone-600 shrink-0"
            title="Close editor"
          >
            <X className="w-5 h-5" />
          </button>
          <input
            type="text"
            value={name}
            onChange={e => { setName(e.target.value); setDirty(true) }}
            className="text-lg font-semibold text-stone-800 bg-transparent border-none outline-none flex-1 min-w-0"
            placeholder="Map name..."
          />
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {dirty && <span className="text-xs text-stone-400">unsaved</span>}
          {error && <span className="text-xs text-red-500 max-w-48 truncate">{error}</span>}
          <button
            onClick={() => doSave()}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-sage-600 text-white rounded-lg text-sm font-medium hover:bg-sage-700 disabled:opacity-50 transition-colors"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save
          </button>
          {savedId && (
            <button
              onClick={() => { onSave(savedId); onClose() }}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-sage-300 text-sage-700 rounded-lg text-sm font-medium hover:bg-sage-50 transition-colors"
            >
              <Play className="w-4 h-4" /> Study This
            </button>
          )}
        </div>
      </div>

      {/* Mindmapper container */}
      <div
        ref={containerRef}
        className="flex-1 outline-none"
        tabIndex={0}
      />
    </div>
  )
}
