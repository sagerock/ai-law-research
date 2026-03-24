'use client'

import { useState, useEffect } from 'react'
import { BookOpen, ChevronDown, ChevronUp, ExternalLink, Scale, FileText, Gavel } from 'lucide-react'
import Link from 'next/link'
import { API_URL } from '@/lib/api'

interface LibraryDoc {
  id: number
  title: string
  doc_type: string
  jurisdiction: string | null
}

// Core SJ cases that are always available (hard-coded IDs match the database)
const CORE_CASES = {
  procedural: [
    {
      id: '111722',
      title: 'Celotex Corp. v. Catrett',
      cite: '477 U.S. 317 (1986)',
      description: "Movant's burden on SJ; established the 'show me' (absence of evidence) motion",
    },
    {
      id: '111719',
      title: 'Anderson v. Liberty Lobby, Inc.',
      cite: '477 U.S. 242 (1986)',
      description: '"Genuine dispute" means a reasonable jury could find for the non-movant',
    },
    {
      id: '2672535',
      title: 'Tolan v. Cotton',
      cite: '572 U.S. 650 (2014)',
      description: 'Court must draw all reasonable inferences in favor of the non-movant',
    },
  ],
  ohio_substantive: [
    {
      id: '4025863',
      title: 'Mudrich v. Standard Oil Co.',
      cite: '153 Ohio St. 31 (1950)',
      description: 'Intervening cause does not break causation if reasonably foreseeable',
    },
    {
      id: '6867332',
      title: 'Cascone v. Herb Kay Co.',
      cite: '6 Ohio St.3d 155 (1983)',
      description: 'Two-part test for superseding cause; foreseeability question is for the jury',
    },
    {
      id: '6876097',
      title: 'Leibreich v. A.J. Refrigeration, Inc.',
      cite: '67 Ohio St.3d 266 (1993)',
      description: 'Superseding cause is a defense to both negligence and strict liability',
    },
  ],
}

export default function MSJResources() {
  const [expanded, setExpanded] = useState(false)
  const [libraryDocs, setLibraryDocs] = useState<LibraryDoc[]>([])

  useEffect(() => {
    fetch(`${API_URL}/api/v1/msj/library`)
      .then((r) => r.json())
      .then(setLibraryDocs)
      .catch(() => {})
  }, [])

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-6 mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-sage-100 rounded-lg flex items-center justify-center">
            <BookOpen className="h-5 w-5 text-sage-700" />
          </div>
          <div className="text-left">
            <h2 className="text-lg font-medium text-stone-900">Approved Sources</h2>
            <p className="text-sm text-stone-500">
              Cases, rules, and resources the AI can cite in your motion
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-stone-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-stone-400" />
        )}
      </button>

      {expanded && (
        <div className="mt-5 space-y-5">
          {/* Procedural cases */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Scale className="h-4 w-4 text-sage-600" />
              <h3 className="text-sm font-medium text-stone-700">
                Summary Judgment Standard (Federal)
              </h3>
            </div>
            <div className="space-y-2">
              {CORE_CASES.procedural.map((c) => (
                <Link
                  key={c.id}
                  href={`/case/${c.id}`}
                  target="_blank"
                  className="block p-3 bg-stone-50 rounded-lg hover:bg-sage-50 transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-sm font-medium text-stone-800 group-hover:text-sage-800">
                        {c.title}
                      </span>
                      <span className="text-xs text-stone-500 ml-1">{c.cite}</span>
                      <p className="text-xs text-stone-500 mt-0.5">{c.description}</p>
                    </div>
                    <ExternalLink className="h-3.5 w-3.5 text-stone-300 group-hover:text-sage-500 flex-shrink-0 mt-0.5" />
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Ohio substantive cases */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Gavel className="h-4 w-4 text-sage-600" />
              <h3 className="text-sm font-medium text-stone-700">
                Ohio Superseding Cause Doctrine
              </h3>
            </div>
            <div className="space-y-2">
              {CORE_CASES.ohio_substantive.map((c) => (
                <Link
                  key={c.id}
                  href={`/case/${c.id}`}
                  target="_blank"
                  className="block p-3 bg-stone-50 rounded-lg hover:bg-sage-50 transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-sm font-medium text-stone-800 group-hover:text-sage-800">
                        {c.title}
                      </span>
                      <span className="text-xs text-stone-500 ml-1">{c.cite}</span>
                      <p className="text-xs text-stone-500 mt-0.5">{c.description}</p>
                    </div>
                    <ExternalLink className="h-3.5 w-3.5 text-stone-300 group-hover:text-sage-500 flex-shrink-0 mt-0.5" />
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Rule 56 */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-4 w-4 text-sage-600" />
              <h3 className="text-sm font-medium text-stone-700">Rules</h3>
            </div>
            <Link
              href="/rules/rule-56"
              target="_blank"
              className="block p-3 bg-stone-50 rounded-lg hover:bg-sage-50 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-sm font-medium text-stone-800 group-hover:text-sage-800">
                    Fed. R. Civ. P. 56
                  </span>
                  <span className="text-xs text-stone-500 ml-1">Summary Judgment</span>
                  <p className="text-xs text-stone-500 mt-0.5">
                    The procedural rule governing motions for summary judgment in federal court
                  </p>
                </div>
                <ExternalLink className="h-3.5 w-3.5 text-stone-300 group-hover:text-sage-500 flex-shrink-0 mt-0.5" />
              </div>
            </Link>
          </div>

          {/* Library resources */}
          {libraryDocs.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <BookOpen className="h-4 w-4 text-sage-600" />
                <h3 className="text-sm font-medium text-stone-700">
                  Reference Library ({libraryDocs.length} resources)
                </h3>
              </div>
              <div className="space-y-1">
                {libraryDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 px-3 py-2 text-xs text-stone-600 bg-stone-50 rounded"
                  >
                    <span className="px-1.5 py-0.5 bg-stone-200 text-stone-500 rounded text-[10px]">
                      {doc.doc_type}
                    </span>
                    <span className="truncate">{doc.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
