import { Metadata } from 'next'
import type { ReactNode } from 'react'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import Header from '@/components/Header'
import { sanitizeLegalHtml } from '@/lib/sanitizeHtml'
import { BRAND_NAME } from '@/lib/site'
import '../reader.css'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Block { type: string; group_id: number | null; html: string; anchor: string | null }
interface Chapter { slug: string; title: string; prev: string | null; next: string | null; blocks: Block[] }
interface TocSection { section: string; anchor: string | null }
interface TocChapter { slug: string; title: string; sections: TocSection[] }
interface Toc { textbook_id: number; chapters: TocChapter[] }

interface PageProps { params: Promise<{ id: string; chapter: string }> }

async function getChapter(id: string, chapter: string): Promise<Chapter | null> {
  try {
    const r = await fetch(`${API_URL}/api/v1/textbooks/${id}/read/${chapter}`, { next: { revalidate: 3600 } })
    if (!r.ok) return null
    return r.json()
  } catch { return null }
}
async function getToc(id: string): Promise<Toc | null> {
  try {
    const r = await fetch(`${API_URL}/api/v1/textbooks/${id}/contents`, { next: { revalidate: 3600 } })
    if (!r.ok) return null
    return r.json()
  } catch { return null }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id, chapter } = await params
  const ch = await getChapter(id, chapter)
  if (!ch) return { title: `Reader | ${BRAND_NAME}` }
  const title = ch.title.replace(/\s+/g, ' ').trim()
  return {
    title: `${title} | Evidence (Cheng) | ${BRAND_NAME}`,
    description: `Read ${title} from Edward K. Cheng's open-source Evidence casebook, free on ${BRAND_NAME}.`,
  }
}

const GROUP_LABEL = new Set(['rule', 'note', 'problem'])

function renderMember(b: Block, i: number) {
  const id = b.anchor || undefined
  const dangerous = { dangerouslySetInnerHTML: { __html: sanitizeLegalHtml(b.html) } }
  switch (b.type) {
    case 'rule': case 'note': case 'problem':
      return <p key={i} id={id} className="label" {...dangerous} />
    case 'quote':
      return <blockquote key={i} id={id} {...dangerous} />
    case 'table':
      return <div key={i} {...dangerous} />
    case 'diagram':
      return <div key={i} id={id} className="cb-diagram" {...dangerous} />
    case 'image':
      return <figure key={i} id={id} className="cb-figure" {...dangerous} />
    default:
      return <p key={i} id={id} {...dangerous} />
  }
}

function renderBlocks(blocks: Block[]) {
  const out: ReactNode[] = []
  let i = 0
  while (i < blocks.length) {
    const b = blocks[i]
    if (b.type === 'chapter-title') { i++; continue } // title shown in the page header
    if (b.group_id != null) {
      const run = [b]
      while (i + 1 < blocks.length && blocks[i + 1].group_id === b.group_id) { i++; run.push(blocks[i]) }
      const boxClass = GROUP_LABEL.has(run[0].type) ? run[0].type : 'note'
      out.push(<div key={i} className={boxClass}>{run.map(renderMember)}</div>)
      i++
      continue
    }
    const id = b.anchor || undefined
    const dangerous = { dangerouslySetInnerHTML: { __html: sanitizeLegalHtml(b.html) } }
    switch (b.type) {
      case 'section': out.push(<h2 key={i} id={id} className="cb-section" {...dangerous} />); break
      case 'subsection': out.push(<h3 key={i} id={id} className="cb-subsection" {...dangerous} />); break
      case 'case': out.push(<h3 key={i} id={id} className="cb-case" {...dangerous} />); break
      case 'judge': out.push(<p key={i} id={id} className="cb-judge" {...dangerous} />); break
      case 'quote': out.push(<blockquote key={i} id={id} {...dangerous} />); break
      case 'diagram': out.push(<div key={i} id={id} className="cb-diagram" {...dangerous} />); break
      case 'image': out.push(<figure key={i} id={id} className="cb-figure" {...dangerous} />); break
      case 'table': out.push(<div key={i} {...dangerous} />); break
      case 'divider': out.push(<hr key={i} id={id} />); break
      default: out.push(<p key={i} id={id} {...dangerous} />)
    }
    i++
  }
  return out
}

export default async function ChapterReader({ params }: PageProps) {
  const { id, chapter } = await params
  const [ch, toc] = await Promise.all([getChapter(id, chapter), getToc(id)])
  if (!ch) notFound()

  return (
    <div className="min-h-screen bg-stone-50">
      <Header />
      <div className="max-w-6xl mx-auto px-4 py-8 flex gap-8">
        {/* TOC sidebar */}
        <aside className="hidden lg:block w-64 shrink-0">
          <div className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto pr-2">
            <Link href={`/textbooks/${id}`} className="inline-flex items-center gap-1 text-sm text-stone-500 hover:text-stone-800 mb-4">
              <ArrowLeft className="h-4 w-4" /> Back to textbook
            </Link>
            <nav className="text-sm space-y-1">
              {toc?.chapters.map((c) => (
                <div key={c.slug}>
                  <Link
                    href={`/textbooks/${id}/read/${c.slug}`}
                    className={`block py-1 ${c.slug === chapter ? 'font-semibold text-sage-700' : 'text-stone-600 hover:text-stone-900'}`}
                  >
                    {c.title.replace(/\s+/g, ' ').trim()}
                  </Link>
                  {c.slug === chapter && c.sections.length > 0 && (
                    <div className="ml-3 border-l border-stone-200 pl-3 py-1 space-y-1">
                      {c.sections.map((s) => (
                        <a key={s.section} href={s.anchor ? `#${s.anchor}` : undefined}
                           className="block text-stone-500 hover:text-sage-700 text-[13px]">
                          {s.section}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </nav>
          </div>
        </aside>

        {/* Chapter body */}
        <main className="min-w-0 flex-1 max-w-3xl">
          <p className="text-xs uppercase tracking-wider text-sage-600 font-sans font-semibold mb-6">
            {ch.title.replace(/\s+/g, ' ').trim()}
          </p>
          <article className="cb-reader">{renderBlocks(ch.blocks)}</article>

          <div className="mt-12 flex justify-between border-t border-stone-200 pt-6 text-sm">
            {ch.prev
              ? <Link href={`/textbooks/${id}/read/${ch.prev}`} className="text-sage-700 hover:underline">← Previous chapter</Link>
              : <span />}
            {ch.next
              ? <Link href={`/textbooks/${id}/read/${ch.next}`} className="text-sage-700 hover:underline">Next chapter →</Link>
              : <span />}
          </div>

          <p className="mt-10 pt-6 border-t border-stone-100 text-xs text-stone-400 leading-relaxed">
            <em>Evidence</em> by Edward K. Cheng, reformatted for the web by {BRAND_NAME} and licensed under{' '}
            <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/" className="underline hover:text-sage-700"
               target="_blank" rel="noopener noreferrer">CC BY-NC-SA 4.0</a>.
          </p>
        </main>
      </div>
    </div>
  )
}
