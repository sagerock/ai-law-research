/**
 * Thin wrapper over gtag (GA4).
 *
 * Every call is best-effort: it no-ops on the server, when GA is not configured
 * (local dev has no NEXT_PUBLIC_GA_ID), and when an ad blocker has removed gtag.
 * Analytics must never interrupt reading.
 */

export type AnalyticsEvent =
  // GA4 recommended names — these light up built-in reports.
  | 'search'
  | 'select_content'
  | 'sign_up'
  | 'login'
  // Tortwell-specific.
  | 'brief_view'
  | 'brief_generate'
  | 'brief_blocked'
  | 'bookmark_add'
  | 'signup_intent'
  | 'study_session_start'
  | 'donate_click'

type AnalyticsParams = Record<string, string | number | boolean>

type GtagFn = (command: string, name: string, params?: AnalyticsParams) => void

function getGtag(): GtagFn | null {
  if (typeof window === 'undefined') return null
  const gtag = (window as unknown as { gtag?: GtagFn }).gtag
  return typeof gtag === 'function' ? gtag : null
}

export function track(name: AnalyticsEvent, params: AnalyticsParams = {}) {
  const gtag = getGtag()
  if (!gtag) return
  try {
    gtag('event', name, params)
  } catch {
    // Never let analytics break a page.
  }
}
