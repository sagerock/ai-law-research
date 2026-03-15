import type { Metadata } from 'next'
import Link from 'next/link'
import {
  Key,
  Shield,
  Zap,
  DollarSign,
  ArrowRight,
  ExternalLink,
  CheckCircle2,
  HelpCircle,
  Sparkles,
  Lock,
  Eye,
  BookOpen,
  MessageSquare,
  ChevronRight,
  Heart,
} from 'lucide-react'

export const metadata: Metadata = {
  title: 'Bring Your Own Key',
  description: 'Use your own Anthropic API key for unlimited AI-powered study tools on Law Study Group.',
}

function StepCard({ number, title, children }: { number: number; title: string; children: React.ReactNode }) {
  return (
    <div className="relative pl-16">
      <div className="absolute left-0 top-0 w-11 h-11 rounded-full bg-sage-700 text-white flex items-center justify-center font-display text-xl">
        {number}
      </div>
      <div>
        <h3 className="text-lg font-semibold text-stone-900 mb-2">{title}</h3>
        <div className="text-stone-600 text-[15px] leading-relaxed space-y-2">{children}</div>
      </div>
    </div>
  )
}

function ComparisonRow({ feature, free, byok }: { feature: string; free: string; byok: string }) {
  return (
    <tr className="border-b border-stone-100 last:border-0">
      <td className="py-3 pr-4 text-sm text-stone-700 font-medium">{feature}</td>
      <td className="py-3 px-4 text-sm text-stone-500 text-center">{free}</td>
      <td className="py-3 pl-4 text-sm text-sage-700 text-center font-medium">{byok}</td>
    </tr>
  )
}

function FAQItem({ question, children }: { question: string; children: React.ReactNode }) {
  return (
    <details className="group border-b border-stone-200 last:border-0">
      <summary className="flex items-center justify-between py-4 cursor-pointer list-none">
        <span className="text-[15px] font-medium text-stone-900 pr-4">{question}</span>
        <ChevronRight className="h-4 w-4 text-stone-400 flex-shrink-0 transition-transform group-open:rotate-90" />
      </summary>
      <div className="pb-4 text-sm text-stone-600 leading-relaxed">{children}</div>
    </details>
  )
}

export default function BYOKPage() {
  return (
    <div className="min-h-screen bg-cream">
      {/* Hero */}
      <div className="relative overflow-hidden bg-gradient-to-b from-sage-800 to-sage-900">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-[15%] w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-[10%] w-96 h-96 bg-sage-400 rounded-full blur-3xl" />
        </div>

        <div className="relative container mx-auto px-4 pt-8 pb-16">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sage-300 hover:text-white text-sm mb-10 transition-colors"
          >
            <ArrowRight className="h-3.5 w-3.5 rotate-180" />
            Back to Law Study Group
          </Link>

          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/10 backdrop-blur rounded-full text-sage-200 text-xs font-medium mb-6 border border-white/10">
              <Key className="h-3.5 w-3.5" />
              Bring Your Own Key
            </div>

            <h1 className="font-display text-4xl sm:text-5xl text-white mb-5 leading-[1.15]">
              Unlock unlimited AI<br className="hidden sm:block" /> with your own API key
            </h1>

            <p className="text-lg text-sage-200 leading-relaxed max-w-2xl mb-8">
              Law Study Group is free for everyone. But if you want unlimited access to our
              most powerful AI features, you can use your own Anthropic API key &mdash; no
              subscription, no middleman. You pay Anthropic directly at their cost.
            </p>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/profile"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-sage-800 rounded-lg font-medium hover:bg-sage-50 transition-colors text-sm"
              >
                <Key className="h-4 w-4" />
                Add Your Key
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 px-5 py-2.5 border border-white/20 text-white rounded-lg font-medium hover:bg-white/10 transition-colors text-sm"
              >
                Learn How It Works
              </a>
            </div>
          </div>
        </div>
      </div>

      <main className="container mx-auto px-4 max-w-4xl">

        {/* What You Get */}
        <section className="-mt-6 relative z-10 mb-12">
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              {
                icon: Zap,
                title: 'Claude Sonnet',
                desc: 'Upgraded from Haiku to Anthropic\'s most capable fast model',
                color: 'text-amber-500',
              },
              {
                icon: Sparkles,
                title: 'Unlimited Messages',
                desc: 'No daily cap on study chat, case Q&A, or brief generation',
                color: 'text-sage-600',
              },
              {
                icon: DollarSign,
                title: '~$3–$8/month',
                desc: 'Typical student usage. You only pay for what you use.',
                color: 'text-green-600',
              },
            ].map((item) => (
              <div
                key={item.title}
                className="bg-white rounded-xl border border-stone-200 p-5 shadow-sm"
              >
                <item.icon className={`h-6 w-6 ${item.color} mb-3`} />
                <h3 className="font-semibold text-stone-900 mb-1">{item.title}</h3>
                <p className="text-sm text-stone-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Comparison Table */}
        <section className="mb-14">
          <h2 className="font-display text-2xl text-stone-900 mb-6">Free vs. BYOK</h2>
          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-stone-200 bg-stone-50">
                  <th className="py-3 pr-4 pl-5 text-left text-xs font-semibold text-stone-500 uppercase tracking-wider">Feature</th>
                  <th className="py-3 px-4 text-center text-xs font-semibold text-stone-500 uppercase tracking-wider">Free</th>
                  <th className="py-3 pl-4 pr-5 text-center text-xs font-semibold text-sage-700 uppercase tracking-wider">BYOK</th>
                </tr>
              </thead>
              <tbody className="px-5">
                <ComparisonRow feature="AI Model" free="Claude Haiku" byok="Claude Sonnet" />
                <ComparisonRow feature="Study Chat" free="15 msgs/day" byok="Unlimited" />
                <ComparisonRow feature="Case Q&A" free="15 msgs/day" byok="Unlimited" />
                <ComparisonRow feature="Brief Generation" free="Site-funded" byok="Your key" />
                <ComparisonRow feature="Case Search" free="Unlimited" byok="Unlimited" />
                <ComparisonRow feature="Bookmarks & Collections" free="Unlimited" byok="Unlimited" />
                <ComparisonRow feature="Monthly Cost" free="$0" byok="~$3–$8 to Anthropic" />
              </tbody>
            </table>
          </div>
          <p className="text-xs text-stone-400 mt-3 text-center">
            Everything stays free forever. BYOK just upgrades AI quality and removes daily limits.
          </p>
        </section>

        {/* How It Works */}
        <section className="mb-14" id="how-it-works">
          <h2 className="font-display text-2xl text-stone-900 mb-8">How to set it up</h2>
          <div className="space-y-10">
            <StepCard number={1} title="Create an Anthropic account">
              <p>
                Go to{' '}
                <a
                  href="https://console.anthropic.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sage-700 underline underline-offset-2 hover:text-sage-600 inline-flex items-center gap-0.5"
                >
                  console.anthropic.com
                  <ExternalLink className="h-3 w-3" />
                </a>{' '}
                and sign up. It takes about 30 seconds &mdash; just an email and password.
              </p>
            </StepCard>

            <StepCard number={2} title="Add billing (pay-as-you-go)">
              <p>
                In the Anthropic console, go to <strong>Settings &rarr; Billing</strong> and add a payment method.
                There&apos;s no monthly minimum. You only pay for the API calls you actually make.
              </p>
              <p>
                Most law students spend <strong>$3&ndash;$8/month</strong> depending on usage.
                A single study chat message costs roughly $0.01&ndash;$0.03.
              </p>
            </StepCard>

            <StepCard number={3} title="Generate an API key">
              <p>
                Go to{' '}
                <a
                  href="https://console.anthropic.com/settings/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sage-700 underline underline-offset-2 hover:text-sage-600 inline-flex items-center gap-0.5"
                >
                  Settings &rarr; API Keys
                  <ExternalLink className="h-3 w-3" />
                </a>{' '}
                and click <strong>Create Key</strong>. Give it a name like &ldquo;Law Study Group&rdquo; and copy the key.
                It starts with <code className="bg-stone-100 px-1.5 py-0.5 rounded text-xs font-mono">sk-ant-</code>.
              </p>
            </StepCard>

            <StepCard number={4} title="Paste it into your profile">
              <p>
                Go to your{' '}
                <Link href="/profile" className="text-sage-700 underline underline-offset-2 hover:text-sage-600">
                  Profile &rarr; AI Settings
                </Link>{' '}
                section and paste the key. We&apos;ll validate it with a quick test call, encrypt it, and store it securely.
                That&apos;s it &mdash; you&apos;re upgraded instantly.
              </p>
            </StepCard>
          </div>
        </section>

        {/* Security */}
        <section className="mb-14">
          <h2 className="font-display text-2xl text-stone-900 mb-6">Your key is safe</h2>
          <div className="bg-white rounded-xl border p-6">
            <div className="grid sm:grid-cols-2 gap-6">
              {[
                {
                  icon: Lock,
                  title: 'Encrypted at rest',
                  desc: 'Your key is encrypted with Fernet symmetric encryption before it touches the database. The raw key is never stored.',
                },
                {
                  icon: Eye,
                  title: 'Never exposed',
                  desc: 'We only show you a preview (sk-ant-...xxxx). The full key is never sent back to the browser or included in logs.',
                },
                {
                  icon: Shield,
                  title: 'You stay in control',
                  desc: 'Remove your key from your profile at any time and it\'s deleted immediately. You can also revoke it from the Anthropic console.',
                },
                {
                  icon: BookOpen,
                  title: 'Only used for study tools',
                  desc: 'Your key is only used for your own study chat, case Q&A, and brief generation. Nothing else.',
                },
              ].map((item) => (
                <div key={item.title} className="flex gap-3">
                  <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-sage-50 flex items-center justify-center">
                    <item.icon className="h-4.5 w-4.5 text-sage-700" />
                  </div>
                  <div>
                    <h3 className="font-medium text-stone-900 text-sm mb-0.5">{item.title}</h3>
                    <p className="text-sm text-stone-500 leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Cost Breakdown */}
        <section className="mb-14">
          <h2 className="font-display text-2xl text-stone-900 mb-6">What it actually costs</h2>
          <div className="bg-white rounded-xl border p-6 space-y-5">
            <p className="text-stone-600 text-[15px] leading-relaxed">
              Anthropic charges per token (roughly per word). Here&apos;s what typical law student usage looks like:
            </p>

            <div className="grid sm:grid-cols-3 gap-4">
              {[
                {
                  label: 'Study chat message',
                  cost: '~$0.01–$0.03',
                  detail: 'Depends on conversation length',
                },
                {
                  label: 'Case brief generation',
                  cost: '~$0.03',
                  detail: 'One-time per case, then cached',
                },
                {
                  label: 'Case Q&A question',
                  cost: '~$0.01–$0.02',
                  detail: 'Per question about a case',
                },
              ].map((item) => (
                <div key={item.label} className="bg-stone-50 rounded-lg p-4 text-center">
                  <p className="text-xl font-bold text-stone-900 mb-1">{item.cost}</p>
                  <p className="text-sm font-medium text-stone-700">{item.label}</p>
                  <p className="text-xs text-stone-400 mt-0.5">{item.detail}</p>
                </div>
              ))}
            </div>

            <div className="bg-sage-50 rounded-lg p-4 border border-sage-100">
              <p className="text-sm text-sage-800">
                <strong>Typical monthly bill:</strong> A student who uses study chat daily and generates
                a few briefs per week usually spends <strong>$3&ndash;$8/month</strong>. Heavy exam-prep
                usage might be $10&ndash;$15. You can set a spending limit in the Anthropic console to
                stay within budget.
              </p>
            </div>

            <p className="text-xs text-stone-400">
              Prices based on Claude Sonnet 4.6: $3/million input tokens, $15/million output tokens.
              Anthropic may adjust pricing over time.
            </p>
          </div>
        </section>

        {/* What Free Users Get */}
        <section className="mb-14">
          <h2 className="font-display text-2xl text-stone-900 mb-6">What you get for free</h2>
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <p className="text-stone-600 text-[15px] leading-relaxed">
              The free tier is not a trial &mdash; it&apos;s the real product. Every student gets:
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              {[
                { icon: BookOpen, text: 'Unlimited case search and reading' },
                { icon: Sparkles, text: 'AI case briefs (funded by the community pool)' },
                { icon: MessageSquare, text: '15 study chat messages per day' },
                { icon: MessageSquare, text: '15 case Q&A questions per day' },
              ].map((item) => (
                <div key={item.text} className="flex items-center gap-2.5">
                  <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                  <span className="text-sm text-stone-700">{item.text}</span>
                </div>
              ))}
            </div>
            <p className="text-sm text-stone-500">
              Bookmarks, collections, outlines, and cached briefs are always unlimited and free.
              BYOK is for power users who want the Sonnet model upgrade and no daily message limits.
            </p>
          </div>
        </section>

        {/* Community Pool & Donate */}
        <section className="mb-14">
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl border border-amber-200 p-6 sm:p-8">
            <div className="flex items-start gap-4">
              <Heart className="h-8 w-8 text-red-400 flex-shrink-0 mt-1" />
              <div>
                <h2 className="text-xl font-bold text-stone-900 mb-2">Don&apos;t want to manage an API key?</h2>
                <p className="text-stone-600 text-[15px] leading-relaxed mb-3">
                  Free AI features are powered by a community pool &mdash; a shared fund that covers the cost of
                  AI calls for everyone. When the pool has funds, all students can generate briefs, chat, and
                  ask questions. When it runs out, AI features pause until someone tops it up.
                </p>
                <p className="text-stone-600 text-[15px] leading-relaxed mb-4">
                  You can help keep the pool funded by buying a coffee on Ko-fi. Every donation goes directly
                  to AI costs, and you can see exactly where the money goes on the{' '}
                  <Link href="/transparency" className="text-amber-700 underline underline-offset-2 hover:text-amber-600">
                    transparency dashboard
                  </Link>.
                </p>
                <div className="flex flex-wrap gap-3">
                  <a
                    href="https://ko-fi.com/sagelewis"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-[#FF5E5B] hover:bg-[#e54d4a] text-white rounded-lg font-medium text-sm transition-colors shadow-sm"
                  >
                    <Heart className="h-4 w-4" />
                    Buy Me a Coffee
                    <ExternalLink className="h-3.5 w-3.5 opacity-70" />
                  </a>
                  <Link
                    href="/transparency"
                    className="inline-flex items-center gap-2 px-4 py-2 border border-amber-300 text-amber-800 rounded-lg font-medium text-sm hover:bg-amber-100 transition-colors"
                  >
                    See the Pool Balance
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="mb-14">
          <h2 className="font-display text-2xl text-stone-900 mb-6">Frequently asked questions</h2>
          <div className="bg-white rounded-xl border px-6">
            <FAQItem question="Can I use a key from OpenAI or another provider?">
              Not right now. We use Anthropic&apos;s Claude models exclusively because they produce the best
              legal analysis we&apos;ve tested. We may add support for other providers in the future.
            </FAQItem>

            <FAQItem question="What happens to briefs I generate with my key?">
              They get cached in our database just like any other brief. This means the next student
              who looks up that case gets the brief instantly &mdash; your key usage helps the whole community.
            </FAQItem>

            <FAQItem question="Will my key be used for other people's requests?">
              No. Your key is only ever used for <em>your</em> requests. Other users&apos; requests use
              the site&apos;s shared API key or their own BYOK key.
            </FAQItem>

            <FAQItem question="Can I set a spending limit?">
              Yes! In the Anthropic console, go to <strong>Settings &rarr; Limits</strong> and set a monthly
              spending cap. If you hit it, your requests will fail gracefully and you&apos;ll fall back to the
              free tier until the next billing cycle.
            </FAQItem>

            <FAQItem question="What if my key stops working?">
              If your key is revoked, expired, or runs out of credits, you&apos;ll automatically fall back to
              the free tier (Haiku, 15 messages/day). You can add a new key anytime from your profile.
            </FAQItem>

            <FAQItem question="Is this the same as a Pro subscription?">
              Similar benefits, but different mechanism. BYOK means you pay Anthropic directly at their
              wholesale API rates. There&apos;s no markup, no subscription, and no middleman. It&apos;s usually
              cheaper than any subscription model would be.
            </FAQItem>

            <FAQItem question="How does this compare to Quimbee?">
              Quimbee charges $276/year ($23/month) for case briefs and study tools. With BYOK,
              you&apos;re looking at $3&ndash;$8/month for unlimited AI-powered case briefs, study chat, and
              more &mdash; and the base tool is completely free.
            </FAQItem>
          </div>
        </section>

        {/* Final CTA */}
        <section className="mb-16">
          <div className="bg-sage-800 rounded-xl p-8 text-center">
            <h2 className="font-display text-2xl text-white mb-3">Ready to upgrade?</h2>
            <p className="text-sage-200 mb-6 max-w-lg mx-auto text-[15px]">
              Get your API key from Anthropic, paste it in your profile, and start studying with
              unlimited Claude Sonnet access.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <a
                href="https://console.anthropic.com/settings/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white/10 border border-white/20 text-white rounded-lg font-medium hover:bg-white/20 transition-colors text-sm"
              >
                Get API Key
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
              <Link
                href="/profile"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-sage-800 rounded-lg font-medium hover:bg-sage-50 transition-colors text-sm"
              >
                Go to Profile
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t bg-white py-6">
        <div className="container mx-auto px-4 text-center text-sm text-stone-500">
          <p>Built with care for law students everywhere.</p>
        </div>
      </footer>
    </div>
  )
}
