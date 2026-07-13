import Link from 'next/link'
import { TrendingUp } from 'lucide-react'
import { TortoiseMark } from '@/components/TortoiseMark'
import { BRAND_NAME } from '@/lib/site'

// Footer keeps the practitioner tools reachable without cluttering the case-focused
// header. Live at their URLs, just de-emphasized here.
export default function Footer() {
  return (
    <footer className="bg-ink text-stone-300 mt-16">
      <div className="container mx-auto px-4 py-10">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-8">
          <div className="max-w-xs">
            <div className="flex items-center gap-2.5 mb-3">
              <TortoiseMark className="w-8 h-6" onDark />
              <span className="font-display text-xl font-semibold text-cream">{BRAND_NAME}</span>
            </div>
            <p className="text-[13px] leading-relaxed text-stone-400">
              Built by a law student for his classmates. Free forever, funded by
              people who found it useful.
            </p>
            <Link
              href="/transparency"
              className="mt-4 inline-flex items-center gap-2 text-[13px] font-semibold text-honey-300
                         bg-honey-300/10 border border-honey-300/30 rounded-lg px-3.5 py-2
                         hover:bg-honey-300/20 transition-colors"
            >
              <TrendingUp className="h-3.5 w-3.5" />
              Transparency dashboard →
            </Link>
          </div>

          <div className="flex gap-12 flex-wrap">
            <div>
              <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-3">Study</div>
              <ul className="space-y-2 text-sm">
                <li><Link href="/" className="text-stone-300 hover:text-honey-300 transition-colors">Cases</Link></li>
                <li><Link href="/study" className="text-stone-300 hover:text-honey-300 transition-colors">Study tools</Link></li>
                <li><Link href="/outlines" className="text-stone-300 hover:text-honey-300 transition-colors">Outlines</Link></li>
                <li><Link href="/textbooks" className="text-stone-300 hover:text-honey-300 transition-colors">Textbooks</Link></li>
                <li><Link href="/briefcheck" className="text-stone-300 hover:text-honey-300 transition-colors">Brief check</Link></li>
              </ul>
            </div>

            <div>
              <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-3">More tools</div>
              <ul className="space-y-2 text-sm">
                <li><Link href="/msj" className="text-stone-300 hover:text-honey-300 transition-colors">MSJ builder</Link></li>
                <li><Link href="/tools/affidavit" className="text-stone-300 hover:text-honey-300 transition-colors">Affidavit builder</Link></li>
                <li><Link href="/verify" className="text-stone-300 hover:text-honey-300 transition-colors">Citation verifier</Link></li>
              </ul>
            </div>

            <div>
              <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-3">Community</div>
              <ul className="space-y-2 text-sm">
                <li>
                  <a href="https://discord.gg/AcGcKMmMZX" target="_blank" rel="noopener noreferrer"
                     className="text-stone-300 hover:text-honey-300 transition-colors">
                    Discord
                  </a>
                </li>
                <li><Link href="/transparency" className="text-stone-300 hover:text-honey-300 transition-colors">Contribute</Link></li>
              </ul>
            </div>
          </div>
        </div>

        <div className="border-t border-white/10 mt-8 pt-5 flex flex-col sm:flex-row sm:justify-between gap-2 text-xs text-stone-500">
          <span>© {new Date().getFullYear()} {BRAND_NAME} · A free study well for law students</span>
          <span>Not legal advice. Always read the opinion.</span>
        </div>
      </div>
    </footer>
  )
}
