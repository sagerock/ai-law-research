'use client'

import { useEffect, useRef, useState, startTransition } from 'react'
import Link from 'next/link'
import { ArrowLeft, CheckCircle2, Loader2, MessageCircle, Send, ThumbsDown, ThumbsUp, Trash2 } from 'lucide-react'
import OutlineMarkdown from '@/components/outlines/OutlineMarkdown'
import { useAuth } from '@/lib/auth-context'
import { API_URL } from '@/lib/api'
import type { CanonicalOutline, CanonicalOutlineSection } from '@/types'

interface SectionComment {
  id: number
  section_id: number
  content: string
  is_edited: boolean
  is_resolved: boolean
  created_at: string
  is_owner: boolean
  user: {
    username: string | null
    display_name: string | null
    profile_username: string | null
  }
}

export default function CanonicalOutlineClient({ initialOutline }: { initialOutline: CanonicalOutline }) {
  const { session, user } = useAuth()
  const [outline, setOutline] = useState(initialOutline)
  const [expandedComments, setExpandedComments] = useState<number | null>(null)
  const [comments, setComments] = useState<Record<number, SectionComment[]>>({})
  const [commentDrafts, setCommentDrafts] = useState<Record<number, string>>({})
  const [loadingComments, setLoadingComments] = useState<number | null>(null)
  const [savingComment, setSavingComment] = useState<number | null>(null)
  const [voting, setVoting] = useState<number | null>(null)
  const [activeSlug, setActiveSlug] = useState<string | null>(null)
  const navRef = useRef<HTMLElement | null>(null)

  // Scroll-spy: the active section is the last one whose top has crossed a
  // marker 25% down the viewport (falling back to the first section at the top
  // of the page).
  useEffect(() => {
    const sections = outline.sections
      .map(section => document.getElementById(section.slug))
      .filter((el): el is HTMLElement => el !== null)
    if (sections.length === 0) return
    let frame = 0
    const update = () => {
      frame = 0
      const marker = window.innerHeight * 0.25
      let current = sections[0].id
      for (const el of sections) {
        if (el.getBoundingClientRect().top <= marker) current = el.id
        else break
      }
      setActiveSlug(current)
    }
    const onScroll = () => {
      if (!frame) frame = window.requestAnimationFrame(update)
    }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame) window.cancelAnimationFrame(frame)
    }
  }, [outline.sections])

  // Keep the active link visible inside the (internally scrolling) nav.
  useEffect(() => {
    if (!activeSlug || !navRef.current) return
    const link = navRef.current.querySelector<HTMLElement>(`a[href="#${activeSlug}"]`)
    if (!link) return
    const nav = navRef.current
    const linkTop = link.getBoundingClientRect().top - nav.getBoundingClientRect().top + nav.scrollTop
    const linkBottom = linkTop + link.offsetHeight
    if (linkTop < nav.scrollTop) {
      nav.scrollTop = linkTop - 8
    } else if (linkBottom > nav.scrollTop + nav.clientHeight) {
      nav.scrollTop = linkBottom - nav.clientHeight + 8
    }
  }, [activeSlug])

  useEffect(() => {
    if (!session?.access_token) return
    let cancelled = false
    fetch(`${API_URL}/api/v1/canonical-outlines/${initialOutline.slug}`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    }).then(async response => {
      if (!response.ok) return
      const authenticatedOutline: CanonicalOutline = await response.json()
      if (!cancelled) startTransition(() => setOutline(authenticatedOutline))
    }).catch(() => undefined)
    return () => { cancelled = true }
  }, [initialOutline.slug, session?.access_token])

  const authHeaders = (): Record<string, string> => session?.access_token ? {
    Authorization: `Bearer ${session.access_token}`,
    'Content-Type': 'application/json',
  } : { 'Content-Type': 'application/json' }

  const updateSection = (sectionId: number, update: Partial<CanonicalOutlineSection>) => {
    setOutline(current => ({
      ...current,
      sections: current.sections.map(section => section.id === sectionId ? { ...section, ...update } : section),
    }))
  }

  const vote = async (section: CanonicalOutlineSection, value: -1 | 1) => {
    if (!session?.access_token) return
    setVoting(section.id)
    try {
      const voteType = section.user_vote === value ? 0 : value
      const response = await fetch(`${API_URL}/api/v1/canonical-outline-sections/${section.id}/vote`, {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify({ vote_type: voteType }),
      })
      if (!response.ok) throw new Error('Vote failed')
      const result = await response.json()
      updateSection(section.id, result)
    } finally {
      setVoting(null)
    }
  }

  const openComments = async (section: CanonicalOutlineSection) => {
    if (expandedComments === section.id) {
      setExpandedComments(null)
      return
    }
    setExpandedComments(section.id)
    if (comments[section.id]) return
    setLoadingComments(section.id)
    try {
      const response = await fetch(`${API_URL}/api/v1/canonical-outline-sections/${section.id}/comments`, {
        headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
      })
      if (!response.ok) throw new Error('Comments failed to load')
      const result = await response.json()
      setComments(current => ({ ...current, [section.id]: result.comments }))
    } finally {
      setLoadingComments(null)
    }
  }

  const addComment = async (section: CanonicalOutlineSection) => {
    const content = commentDrafts[section.id]?.trim()
    if (!content || !session?.access_token) return
    setSavingComment(section.id)
    try {
      const response = await fetch(`${API_URL}/api/v1/canonical-outline-sections/${section.id}/comments`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ content }),
      })
      if (!response.ok) throw new Error('Comment failed')
      const created: SectionComment = await response.json()
      setComments(current => ({ ...current, [section.id]: [...(current[section.id] || []), created] }))
      setCommentDrafts(current => ({ ...current, [section.id]: '' }))
      updateSection(section.id, { comment_count: section.comment_count + 1 })
    } finally {
      setSavingComment(null)
    }
  }

  const deleteComment = async (section: CanonicalOutlineSection, commentId: number) => {
    if (!session?.access_token) return
    const response = await fetch(`${API_URL}/api/v1/canonical-outline-comments/${commentId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    if (!response.ok) return
    setComments(current => ({
      ...current,
      [section.id]: (current[section.id] || []).filter(comment => comment.id !== commentId),
    }))
    const deleted = (comments[section.id] || []).find(comment => comment.id === commentId)
    if (deleted && !deleted.is_resolved) {
      updateSection(section.id, { comment_count: Math.max(0, section.comment_count - 1) })
    }
  }

  return (
    <main className="min-h-screen bg-cream">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Link href="/study/outlines" className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-sage-700 hover:text-sage-900">
          <ArrowLeft className="h-4 w-4" /> All outlines
        </Link>

        <header className="mb-10 border-b border-sage-200 pb-8">
          <div className="mb-3 flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.16em] text-sage-700">
            <span className="rounded-full bg-sage-100 px-3 py-1.5">Canonical outline</span>
            <span>Version {outline.version}</span>
            <span>{outline.sections.length} sections</span>
          </div>
          <h1 className="max-w-4xl font-display text-4xl font-semibold leading-tight text-stone-900 sm:text-6xl">{outline.title}</h1>
          {outline.description && <p className="mt-4 max-w-3xl text-lg leading-8 text-stone-600">{outline.description}</p>}
          <p className="mt-4 flex items-center gap-2 text-sm text-sage-700">
            <CheckCircle2 className="h-4 w-4" /> Structured by topic and linked to primary sources
          </p>
        </header>

        <div className="grid gap-10 lg:grid-cols-[250px_minmax(0,1fr)]">
          <aside className="hidden lg:block">
            <nav ref={navRef} className="sticky top-24 max-h-[calc(100vh-7rem)] overflow-y-auto overscroll-contain rounded-2xl border border-sage-200 bg-white p-4" aria-label="Outline sections">
              <p className="mb-3 px-2 text-xs font-semibold uppercase tracking-[0.14em] text-stone-500">On this page</p>
              <ol className="space-y-1">
                {outline.sections.map((section, index) => (
                  <li key={section.id}>
                    <a
                      href={`#${section.slug}`}
                      aria-current={activeSlug === section.slug ? 'location' : undefined}
                      className={`flex gap-2 rounded-lg px-2 py-2 text-sm ${activeSlug === section.slug ? 'bg-sage-100 font-medium text-sage-900' : 'text-stone-600 hover:bg-sage-50 hover:text-sage-800'}`}
                    >
                      <span className={activeSlug === section.slug ? 'text-sage-600' : 'text-stone-400'}>{index + 1}.</span>{section.title}
                    </a>
                  </li>
                ))}
              </ol>
            </nav>
          </aside>

          <div className="space-y-6">
            {outline.sections.map((section, index) => (
              <section id={section.slug} key={section.id} className="scroll-mt-24 rounded-2xl border border-stone-200 bg-white p-5 shadow-sm sm:p-8">
                <div className="mb-5 flex items-start gap-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sage-700 text-sm font-bold text-white">{index + 1}</span>
                  <h2 className="font-display text-3xl font-semibold leading-tight text-stone-900">{section.title}</h2>
                </div>
                <OutlineMarkdown markdown={section.body} />

                {section.sources.some(source => source.url) && (
                  <div className="mt-7 border-t border-stone-100 pt-5">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-stone-500">Sources in this section</p>
                    <div className="flex flex-wrap gap-2">
                      {section.sources.filter(source => source.url).map(source => (
                        <Link key={`${source.type}-${source.ref}`} href={source.url!} className="rounded-full bg-honey-100 px-3 py-1.5 text-xs font-semibold text-honey-700 hover:bg-honey-300/40">
                          {source.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-7 flex flex-wrap items-center gap-2 border-t border-stone-100 pt-5">
                  {user ? (
                    <>
                      <button onClick={() => vote(section, 1)} disabled={voting === section.id} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium ${section.user_vote === 1 ? 'bg-sage-700 text-white' : 'bg-sage-50 text-sage-700 hover:bg-sage-100'}`}>
                        <ThumbsUp className="h-4 w-4" /> Clear <span>{section.upvotes}</span>
                      </button>
                      <button onClick={() => vote(section, -1)} disabled={voting === section.id} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium ${section.user_vote === -1 ? 'bg-stone-700 text-white' : 'bg-stone-100 text-stone-600 hover:bg-stone-200'}`}>
                        <ThumbsDown className="h-4 w-4" /> Needs work <span>{section.downvotes}</span>
                      </button>
                    </>
                  ) : (
                    <Link href={`/login?returnTo=${encodeURIComponent(`/outlines/${outline.slug}#${section.slug}`)}`} className="text-sm font-medium text-sage-700 hover:text-sage-900">Sign in to vote</Link>
                  )}
                  <button onClick={() => openComments(section)} className="ml-auto inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-stone-600 hover:bg-stone-100">
                    <MessageCircle className="h-4 w-4" /> Feedback <span>{section.comment_count}</span>
                  </button>
                </div>

                {expandedComments === section.id && (
                  <div className="mt-4 rounded-xl bg-stone-50 p-4 sm:p-5">
                    {loadingComments === section.id ? (
                      <Loader2 className="mx-auto h-5 w-5 animate-spin text-stone-400" />
                    ) : (
                      <div className="space-y-3">
                        {(comments[section.id] || []).map(comment => (
                          <div key={comment.id} className={`rounded-lg border bg-white p-3 ${comment.is_resolved ? 'opacity-60' : ''}`}>
                            <div className="mb-1 flex items-center gap-2 text-xs text-stone-500">
                              <span className="font-semibold text-stone-700">{comment.user.display_name || comment.user.username || 'Student'}</span>
                              <span>{new Date(comment.created_at).toLocaleDateString()}</span>
                              {comment.is_edited && <span>edited</span>}
                              {comment.is_resolved && <span className="text-sage-700">resolved</span>}
                              {comment.is_owner && (
                                <button onClick={() => deleteComment(section, comment.id)} className="ml-auto text-stone-400 hover:text-red-600" aria-label="Delete comment">
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </div>
                            <p className="whitespace-pre-wrap text-sm leading-6 text-stone-700">{comment.content}</p>
                          </div>
                        ))}
                        {(comments[section.id] || []).length === 0 && <p className="text-sm text-stone-500">No feedback yet. Be the first to flag what could be clearer.</p>}
                        {user ? (
                          <div className="flex gap-2 pt-2">
                            <textarea value={commentDrafts[section.id] || ''} onChange={event => setCommentDrafts(current => ({ ...current, [section.id]: event.target.value }))} rows={2} maxLength={5000} placeholder="What is clear, missing, or confusing?" className="min-w-0 flex-1 resize-none rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm outline-none focus:border-sage-500 focus:ring-2 focus:ring-sage-100" />
                            <button onClick={() => addComment(section)} disabled={savingComment === section.id || !commentDrafts[section.id]?.trim()} className="self-end rounded-lg bg-sage-700 p-2.5 text-white hover:bg-sage-600 disabled:bg-stone-300" aria-label="Post feedback">
                              {savingComment === section.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                            </button>
                          </div>
                        ) : (
                          <Link href={`/login?returnTo=${encodeURIComponent(`/outlines/${outline.slug}#${section.slug}`)}`} className="inline-block pt-2 text-sm font-medium text-sage-700">Sign in to leave feedback</Link>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </section>
            ))}
          </div>
        </div>
      </div>
    </main>
  )
}
