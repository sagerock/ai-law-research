import Link from 'next/link'

// Footer keeps the practitioner tools reachable without cluttering the case-focused
// header. Live at their URLs, just de-emphasized here.
export default function Footer() {
  return (
    <footer className="border-t border-stone-200 bg-cream/50 mt-16">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-6">
          <div className="max-w-xs">
            <div className="font-display text-lg text-stone-900">Law Study Group</div>
            <p className="text-xs text-stone-500 mt-1 leading-relaxed">
              Free AI case briefs and an open-data citator for law students.
            </p>
          </div>

          <div className="flex gap-10">
            <div>
              <div className="text-xs font-medium text-stone-400 uppercase tracking-wide mb-2">Study</div>
              <ul className="space-y-1.5 text-sm">
                <li><Link href="/" className="text-stone-600 hover:text-sage-700">Cases</Link></li>
                <li><Link href="/study" className="text-stone-600 hover:text-sage-700">Study tools</Link></li>
                <li><Link href="/textbooks" className="text-stone-600 hover:text-sage-700">Textbooks</Link></li>
                <li><Link href="/briefcheck" className="text-stone-600 hover:text-sage-700">Brief check</Link></li>
              </ul>
            </div>

            <div>
              <div className="text-xs font-medium text-stone-400 uppercase tracking-wide mb-2">More tools</div>
              <ul className="space-y-1.5 text-sm">
                <li><Link href="/msj" className="text-stone-600 hover:text-sage-700">MSJ builder</Link></li>
                <li><Link href="/tools/affidavit" className="text-stone-600 hover:text-sage-700">Affidavit builder</Link></li>
                <li><Link href="/verify" className="text-stone-600 hover:text-sage-700">Citation verifier</Link></li>
                <li><Link href="/transparency" className="text-stone-600 hover:text-sage-700">Transparency</Link></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </footer>
  )
}
