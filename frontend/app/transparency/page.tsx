'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Heart,
  Coffee,
  DollarSign,
  Sparkles,
  Users,
  TrendingUp,
  ExternalLink,
  Server,
  Bot,
  Zap,
} from 'lucide-react'
import Header from '@/components/Header'
import { API_URL } from '@/lib/api'
import { TransparencyStats } from '@/types'

// Progress Bar Component
function ProgressBar({
  value,
  max,
  label,
  sublabel,
  colorClass = 'bg-sage-700',
}: {
  value: number
  max: number
  label: string
  sublabel?: string
  colorClass?: string
}) {
  const percentage = max > 0 ? Math.min(100, (value / max) * 100) : 0

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-end">
        <div>
          <span className="text-sm font-medium text-stone-700">{label}</span>
          {sublabel && (
            <span className="text-xs text-stone-500 ml-2">{sublabel}</span>
          )}
        </div>
        <span className="text-lg font-bold text-stone-900">
          ${value.toFixed(2)}
        </span>
      </div>
      <div className="h-3 bg-stone-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${colorClass} rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

// Stat Card Component
function StatCard({
  icon: Icon,
  label,
  value,
  subtext,
  colorClass = 'text-sage-600'
}: {
  icon: React.ElementType
  label: string
  value: string | number
  subtext?: string
  colorClass?: string
}) {
  return (
    <div className="bg-white rounded-lg border p-6 text-center">
      <Icon className={`h-8 w-8 mx-auto mb-3 ${colorClass}`} />
      <div className="text-3xl font-bold text-stone-900 mb-1">{value}</div>
      <div className="text-sm font-medium text-stone-700">{label}</div>
      {subtext && <div className="text-xs text-stone-500 mt-1">{subtext}</div>}
    </div>
  )
}

export default function TransparencyPage() {
  const [stats, setStats] = useState<TransparencyStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/transparency`)
      if (!response.ok) throw new Error('Failed to load transparency data')
      const data = await response.json()
      setStats(data)
    } catch (err) {
      setError('Unable to load transparency data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cream">
        <div className="container mx-auto px-4 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-stone-200 rounded w-1/3"></div>
            <div className="grid md:grid-cols-3 gap-6">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-32 bg-stone-200 rounded-lg"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-cream">
      <Header />

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Personal Introduction */}
        <div className="bg-white rounded-lg border p-8 mb-8 text-center">
          <h1 className="text-3xl font-bold text-stone-900 mb-4">
            Transparency Dashboard
          </h1>
          <p className="text-lg text-stone-600 max-w-2xl mx-auto leading-relaxed">
            This tool was built to help law students access legal research
            without expensive subscriptions. Here's exactly what it costs to run, because you
            deserve to know where your support goes.
          </p>
        </div>

        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-700">{error}</p>
            <button
              onClick={fetchStats}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
            >
              Try Again
            </button>
          </div>
        ) : stats && (
          <>
            {/* This Month's Costs */}
            <section className="bg-white rounded-lg border p-6 mb-8">
              <h2 className="text-xl font-bold text-stone-900 mb-6 flex items-center">
                <DollarSign className="h-6 w-6 mr-2 text-green-600" />
                {stats.month_name} Costs
              </h2>

              <div className="space-y-6">
                {/* AI Costs */}
                <ProgressBar
                  value={stats.month_ai_cost}
                  max={stats.monthly_goal}
                  label="AI Summaries"
                  sublabel={`(${stats.month_summaries} generated)`}
                  colorClass="bg-sage-500"
                />
                <p className="text-xs text-stone-500 -mt-4">
                  Claude AI generates case briefs at ~$0.03 each
                </p>

                {/* Hosting Costs */}
                <ProgressBar
                  value={stats.month_hosting_cost}
                  max={stats.monthly_goal}
                  label="Hosting (Railway)"
                  colorClass="bg-sage-500"
                />
                <p className="text-xs text-stone-500 -mt-4">
                  Database, API server, and frontend hosting
                </p>

                {/* Total Costs */}
                <div className="pt-4 border-t">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-semibold text-stone-900">Total Monthly Costs</span>
                    <span className="text-xl font-bold text-stone-900">
                      ${stats.month_total_cost.toFixed(2)}
                    </span>
                  </div>
                  <div className="h-4 bg-stone-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-sage-600 to-sage-400 rounded-full transition-all duration-500"
                      style={{ width: `${stats.goal_percent}%` }}
                    />
                  </div>
                  <div className="text-xs text-stone-500 mt-1">
                    {stats.goal_percent.toFixed(1)}% of ${stats.monthly_goal} monthly goal
                  </div>
                </div>

                {/* Donations vs Costs */}
                <div className="pt-4 border-t mt-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-semibold text-stone-900">
                      Donations This Month
                      {stats.monthly_donations_count > 0 && (
                        <span className="text-stone-500 font-normal ml-1">
                          ({stats.monthly_donations_count} supporter{stats.monthly_donations_count !== 1 ? 's' : ''})
                        </span>
                      )}
                    </span>
                    <span className="text-xl font-bold text-green-600">
                      ${stats.monthly_donations.toFixed(2)}
                    </span>
                  </div>
                  <div className="h-4 bg-stone-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, (stats.monthly_donations / stats.month_total_cost) * 100)}%` }}
                    />
                  </div>
                  <div className="text-xs mt-1">
                    {stats.monthly_donations >= stats.month_total_cost ? (
                      <span className="text-green-600 font-medium">
                        Fully funded! Surplus goes to {stats.charity_name}
                      </span>
                    ) : (
                      <span className="text-stone-500">
                        ${(stats.month_total_cost - stats.monthly_donations).toFixed(2)} still needed to cover costs
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* Community AI Pool */}
            <section className="bg-white rounded-lg border p-6 mb-8">
              <h2 className="text-xl font-bold text-stone-900 mb-4 flex items-center">
                <Zap className="h-6 w-6 mr-2 text-amber-500" />
                Community AI Pool
              </h2>

              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-stone-700">Pool Balance</span>
                  <span className={`text-2xl font-bold ${
                    !stats.community_pool_healthy ? 'text-red-500' :
                    stats.community_pool_low ? 'text-amber-500' :
                    'text-green-600'
                  }`}>
                    ${stats.community_pool_balance.toFixed(2)}
                  </span>
                </div>

                <div className="h-3 bg-stone-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      !stats.community_pool_healthy ? 'bg-red-400' :
                      stats.community_pool_low ? 'bg-amber-400' :
                      'bg-green-400'
                    }`}
                    style={{ width: `${Math.min(100, Math.max(3, (stats.community_pool_balance / Math.max(stats.monthly_goal, 1)) * 100))}%` }}
                  />
                </div>

                {!stats.community_pool_healthy ? (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-800 font-medium">
                      AI features are paused — the community pool is empty.
                    </p>
                    <p className="text-xs text-red-700 mt-1">
                      Donate to refill the pool and restore free AI access for all students, or{' '}
                      <a href="/byok" className="underline">add your own API key</a> for unlimited personal access.
                    </p>
                  </div>
                ) : stats.community_pool_low ? (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-sm text-amber-800 font-medium">
                      The pool is running low — help keep AI features available!
                    </p>
                    <p className="text-xs text-amber-700 mt-1">
                      Every dollar funds more AI-powered case briefs for students who can't afford Quimbee.
                    </p>
                  </div>
                ) : (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800 font-medium">
                      Thanks to our donors! The community pool is funded.
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      AI features are available for everyone. Donations keep it going!
                    </p>
                  </div>
                )}

                <p className="text-xs text-stone-500">
                  Ko-fi donations and admin top-ups fund the community AI pool. When the pool is empty, free AI features pause.
                  You can also <a href="/byok" className="underline">bring your own API key</a> for unlimited personal access.
                </p>
              </div>
            </section>

            {/* All-Time Stats */}
            <section className="mb-8">
              <h2 className="text-xl font-bold text-stone-900 mb-4 flex items-center">
                <TrendingUp className="h-6 w-6 mr-2 text-sage-600" />
                All-Time Impact
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  icon={Sparkles}
                  label="Case Briefs"
                  value={stats.total_summaries}
                  subtext="AI-powered"
                  colorClass="text-sage-600"
                />
                <StatCard
                  icon={DollarSign}
                  label="Total Costs"
                  value={`$${stats.total_ai_cost.toFixed(2)}`}
                  subtext="AI summaries"
                  colorClass="text-red-500"
                />
                <StatCard
                  icon={Heart}
                  label="Donations"
                  value={`$${stats.total_donations.toFixed(2)}`}
                  subtext="From supporters"
                  colorClass="text-green-600"
                />
                <StatCard
                  icon={Users}
                  label="Students Helped"
                  value={`${Math.max(10, Math.floor(stats.total_summaries / 3))}+`}
                  subtext="And counting!"
                  colorClass="text-sage-600"
                />
              </div>
            </section>

            {/* Support Section */}
            <section className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg border border-amber-200 p-8">
              <div className="text-center mb-6">
                <Heart className="h-12 w-12 mx-auto mb-4 text-red-500" />
                <h2 className="text-2xl font-bold text-stone-900 mb-2">
                  Support This Project
                </h2>
                <p className="text-stone-600 max-w-lg mx-auto">
                  Any donations beyond monthly costs go directly to <strong>{stats.charity_name}</strong>
                  {stats.charity_description && ` - ${stats.charity_description.toLowerCase()}`}.
                </p>
              </div>

              {/* Ko-fi Button */}
              {stats.kofi_url ? (
                <div className="flex justify-center mb-6">
                  <a
                    href={stats.kofi_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-8 py-4 bg-[#FF5E5B] hover:bg-[#e54d4a] text-white font-bold rounded-lg text-lg transition shadow-lg hover:shadow-xl"
                  >
                    <Coffee className="h-6 w-6 mr-3" />
                    Buy Me a Coffee on Ko-fi
                    <ExternalLink className="h-4 w-4 ml-2 opacity-70" />
                  </a>
                </div>
              ) : (
                <div className="flex justify-center mb-6">
                  <div className="px-8 py-4 bg-stone-100 text-stone-500 rounded-lg text-center">
                    <Coffee className="h-6 w-6 mx-auto mb-2" />
                    <p className="text-sm">Donation link coming soon!</p>
                  </div>
                </div>
              )}

              {/* Charity Info */}
              {stats.charity_url ? (
                <div className="bg-white/50 rounded-lg p-4 text-center">
                  <p className="text-sm text-stone-600 mb-2">
                    Surplus donations support:
                  </p>
                  <a
                    href={stats.charity_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-amber-700 hover:text-amber-800 font-semibold"
                  >
                    {stats.charity_name}
                    <ExternalLink className="h-4 w-4 ml-1" />
                  </a>
                </div>
              ) : (
                <div className="bg-white/50 rounded-lg p-4 text-center">
                  <p className="text-sm text-stone-600">
                    Surplus donations support: <strong>{stats.charity_name}</strong>
                  </p>
                </div>
              )}
            </section>

            {/* Why This Matters */}
            <section className="mt-8 bg-white rounded-lg border p-6">
              <h2 className="text-xl font-bold text-stone-900 mb-4">
                Why Transparency Matters
              </h2>
              <div className="prose prose-neutral max-w-none text-stone-600 space-y-4">
                <p>
                  As law students, we get free Westlaw and Lexis access. But Quimbee? That's $276/year
                  out of our own pockets - on top of tuition, books, and everything else. I built this
                  tool because AI-powered case briefs shouldn't be another expense we have to stress about.
                </p>
                <p>
                  By showing exactly what it costs to run this site, we want you to know that your
                  support directly enables free legal research. There's no hidden profit margin here -
                  just fellow law students trying to help.
                </p>
              </div>
            </section>

            {/* Cost Breakdown */}
            <section className="mt-8 bg-stone-50 rounded-lg border p-6">
              <h3 className="text-lg font-semibold text-stone-900 mb-4">
                How Costs Break Down
              </h3>
              <div className="grid md:grid-cols-2 gap-4 text-sm">
                <div className="flex items-start space-x-3">
                  <Bot className="h-5 w-5 text-sage-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-stone-900">AI Summaries (~$0.03 each)</p>
                    <p className="text-stone-600">
                      Claude AI reads the full case opinion and generates a structured brief with facts, issues, holding, and reasoning.
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <Server className="h-5 w-5 text-sage-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-stone-900">Hosting (~$5-20/month)</p>
                    <p className="text-stone-600">
                      Railway hosts the database, API server, and frontend. Costs scale with usage.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t bg-white py-6 mt-12">
        <div className="container mx-auto px-4 text-center text-sm text-stone-500">
          <p>Built with care for law students everywhere.</p>
        </div>
      </footer>
    </div>
  )
}
