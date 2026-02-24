/**
 * Parse legal citations in text and return segments with link information.
 *
 * Detects patterns like:
 * - Rule 12(b)(6), Rule 56, Fed. R. Civ. P. 12
 * - 28 U.S.C. § 1332, 42 U.S.C. §1983
 */

interface TextSegment {
  text: string
  href?: string  // if present, this segment is a link
}

// FRCP citation patterns
const FRCP_PATTERNS = [
  // "Fed. R. Civ. P. 12" or "FRCP 12" or "F.R.C.P. 12"
  /(?:Fed\.?\s*R\.?\s*Civ\.?\s*P\.?|FRCP|F\.R\.C\.P\.)\s*(\d+(?:\.\d+)?)/gi,
  // "Rule 12(b)(6)" or "Rule 56(a)"
  /\bRule\s+(\d+(?:\.\d+)?)(?:\([a-z0-9]+\))*(?!\s*of\s+(?:the\s+)?(?:Supreme|Federal))/gi,
]

// Federal statute citation pattern: "28 U.S.C. § 1332" or "42 U.S.C. §1983"
const STATUTE_PATTERN = /(\d+)\s+U\.S\.C\.?\s*§\s*(\d+[a-z]?)/gi

function ruleSlug(num: string): string {
  // "12" -> "rule-12", "4.1" -> "rule-4-1"
  return `rule-${num.replace('.', '-')}`
}

function statuteSlug(title: string, section: string): string {
  return `${title}-usc-${section}`
}

export function parseLegalCitations(text: string): TextSegment[] {
  if (!text) return [{ text }]

  // Collect all matches with their positions
  const matches: { start: number; end: number; href: string; text: string }[] = []

  // Find FRCP citations
  for (const pattern of FRCP_PATTERNS) {
    pattern.lastIndex = 0
    let match: RegExpExecArray | null
    while ((match = pattern.exec(text)) !== null) {
      const ruleNum = match[1]
      matches.push({
        start: match.index,
        end: match.index + match[0].length,
        href: `/rules/${ruleSlug(ruleNum)}`,
        text: match[0],
      })
    }
  }

  // Find statute citations
  STATUTE_PATTERN.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = STATUTE_PATTERN.exec(text)) !== null) {
    const title = match[1]
    const section = match[2]
    matches.push({
      start: match.index,
      end: match.index + match[0].length,
      href: `/statutes/${statuteSlug(title, section)}`,
      text: match[0],
    })
  }

  if (matches.length === 0) return [{ text }]

  // Sort by position, deduplicate overlaps (keep longer match)
  matches.sort((a, b) => a.start - b.start)
  const deduped: typeof matches = []
  for (const m of matches) {
    if (deduped.length === 0 || m.start >= deduped[deduped.length - 1].end) {
      deduped.push(m)
    } else if (m.end - m.start > deduped[deduped.length - 1].end - deduped[deduped.length - 1].start) {
      deduped[deduped.length - 1] = m
    }
  }

  // Build segments
  const segments: TextSegment[] = []
  let pos = 0
  for (const m of deduped) {
    if (m.start > pos) {
      segments.push({ text: text.slice(pos, m.start) })
    }
    segments.push({ text: m.text, href: m.href })
    pos = m.end
  }
  if (pos < text.length) {
    segments.push({ text: text.slice(pos) })
  }

  return segments
}
