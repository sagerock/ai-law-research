/**
 * Parse legal citations in text and return segments with link information.
 *
 * Detects patterns like:
 * - Rule 12(b)(6), Rule 56, Fed. R. Civ. P. 12
 * - 28 U.S.C. § 1332, 42 U.S.C. §1983
 * - First Amendment, Fourteenth Amendment, Amendment XIV
 * - Due Process Clause, Equal Protection Clause, Commerce Clause
 */

interface TextSegment {
  text: string
  href?: string  // if present, this segment is a link
}

export interface LegalTextRef {
  label: string
  href: string
  type: 'rule' | 'statute' | 'constitution'
}

// FRCP citation patterns
const FRCP_PATTERNS = [
  // "Fed. R. Civ. P. 12" or "FRCP 12" or "F.R.C.P. 12"
  /(?:Fed\.?\s*R\.?\s*Civ\.?\s*P\.?|FRCP|F\.R\.C\.P\.)\s*(\d+(?:\.\d+)?)/gi,
  // "Rule 12(b)(6)" or "Rule 56(a)"
  /\bRule\s+(\d+(?:\.\d+)?)(?!\d)(?:\([a-z0-9]+\))*(?!\s*of\s+(?:the\s+)?Supreme)/gi,
]

// Federal statute citation pattern: "28 U.S.C. § 1332" or "42 U.S.C. §1983"
const STATUTE_PATTERN = /(\d+)\s+U\.S\.C\.?\s*§\s*(\d+[a-z]?)/gi

// Word-to-number mapping for ordinal amendment names
const ORDINAL_TO_NUM: Record<string, number> = {
  first: 1, second: 2, third: 3, fourth: 4, fifth: 5,
  sixth: 6, seventh: 7, eighth: 8, ninth: 9, tenth: 10,
  eleventh: 11, twelfth: 12, thirteenth: 13, fourteenth: 14,
  fifteenth: 15, sixteenth: 16, seventeenth: 17, eighteenth: 18,
  nineteenth: 19, twentieth: 20, 'twenty-first': 21, 'twenty-second': 22,
  'twenty-third': 23, 'twenty-fourth': 24, 'twenty-fifth': 25,
  'twenty-sixth': 26, 'twenty-seventh': 27,
}

// Roman numeral to number
const ROMAN_TO_NUM: Record<string, number> = {
  I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6, VII: 7,
  VIII: 8, IX: 9, X: 10, XI: 11, XII: 12, XIII: 13, XIV: 14,
  XV: 15, XVI: 16, XVII: 17, XVIII: 18, XIX: 19, XX: 20,
  XXI: 21, XXII: 22, XXIII: 23, XXIV: 24, XXV: 25, XXVI: 26, XXVII: 27,
}

// Named clauses → amendment/article they belong to
const NAMED_CLAUSES: { pattern: RegExp; amendment: number; article?: number; label: string }[] = [
  { pattern: /\bDue\s+Process\s+Clause\b/gi, amendment: 14, label: 'Due Process Clause' },
  { pattern: /\bEqual\s+Protection\s+Clause\b/gi, amendment: 14, label: 'Equal Protection Clause' },
  { pattern: /\bEstablishment\s+Clause\b/gi, amendment: 1, label: 'Establishment Clause' },
  { pattern: /\bFree\s+Exercise\s+Clause\b/gi, amendment: 1, label: 'Free Exercise Clause' },
  { pattern: /\bTakings\s+Clause\b/gi, amendment: 5, label: 'Takings Clause' },
  { pattern: /\bConfrontation\s+Clause\b/gi, amendment: 6, label: 'Confrontation Clause' },
  { pattern: /\bCruel\s+and\s+Unusual\s+Punishment\b/gi, amendment: 8, label: 'Cruel and Unusual Punishment' },
  { pattern: /\bCommerce\s+Clause\b/gi, amendment: 0, article: 1, label: 'Commerce Clause' },
  { pattern: /\bSupremacy\s+Clause\b/gi, amendment: 0, article: 6, label: 'Supremacy Clause' },
  { pattern: /\bNecessary\s+and\s+Proper\s+Clause\b/gi, amendment: 0, article: 1, label: 'Necessary and Proper Clause' },
  { pattern: /\bFull\s+Faith\s+and\s+Credit\s+Clause\b/gi, amendment: 0, article: 4, label: 'Full Faith and Credit Clause' },
]

// Ordinal amendment pattern: "First Amendment", "Fourteenth Amendment"
const ORDINAL_WORDS = Object.keys(ORDINAL_TO_NUM).join('|')
const ORDINAL_AMENDMENT_PATTERN = new RegExp(
  `\\b(${ORDINAL_WORDS})\\s+Amendment\\b`, 'gi'
)

// Numeric ordinal: "1st Amendment", "14th Amendment"
const NUMERIC_ORDINAL_AMENDMENT = /\b(\d+)(?:st|nd|rd|th)\s+Amendment\b/gi

// Roman numeral form: "Amendment XIV", "Amendment I"
const ROMAN_KEYS = Object.keys(ROMAN_TO_NUM).join('|')
const ROMAN_AMENDMENT_PATTERN = new RegExp(
  `\\bAmendment\\s+(${ROMAN_KEYS})\\b`, 'gi'
)

// Article references: "Article I", "Article III"
const ARTICLE_PATTERN = new RegExp(
  `\\bArticle\\s+(${ROMAN_KEYS})\\b`, 'gi'
)

function ruleSlug(num: string): string {
  // "12" -> "rule-12", "4.1" -> "rule-4-1"
  return `rule-${num.replace('.', '-')}`
}

function statuteSlug(title: string, section: string): string {
  return `${title}-usc-${section}`
}

type MatchInfo = { start: number; end: number; href: string; text: string; type: 'rule' | 'statute' | 'constitution' }

function collectMatches(text: string): MatchInfo[] {
  const matches: MatchInfo[] = []

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
        type: 'rule',
      })
    }
  }

  // Find statute citations
  STATUTE_PATTERN.lastIndex = 0
  let sMatch: RegExpExecArray | null
  while ((sMatch = STATUTE_PATTERN.exec(text)) !== null) {
    const title = sMatch[1]
    const section = sMatch[2]
    matches.push({
      start: sMatch.index,
      end: sMatch.index + sMatch[0].length,
      href: `/statutes/${statuteSlug(title, section)}`,
      text: sMatch[0],
      type: 'statute',
    })
  }

  // Find ordinal amendment references ("Fourteenth Amendment")
  ORDINAL_AMENDMENT_PATTERN.lastIndex = 0
  let oMatch: RegExpExecArray | null
  while ((oMatch = ORDINAL_AMENDMENT_PATTERN.exec(text)) !== null) {
    const num = ORDINAL_TO_NUM[oMatch[1].toLowerCase()]
    if (num) {
      matches.push({
        start: oMatch.index,
        end: oMatch.index + oMatch[0].length,
        href: `/constitution/amendment-${num}`,
        text: oMatch[0],
        type: 'constitution',
      })
    }
  }

  // Find numeric ordinal amendments ("14th Amendment")
  NUMERIC_ORDINAL_AMENDMENT.lastIndex = 0
  let nMatch: RegExpExecArray | null
  while ((nMatch = NUMERIC_ORDINAL_AMENDMENT.exec(text)) !== null) {
    const num = parseInt(nMatch[1])
    if (num >= 1 && num <= 27) {
      matches.push({
        start: nMatch.index,
        end: nMatch.index + nMatch[0].length,
        href: `/constitution/amendment-${num}`,
        text: nMatch[0],
        type: 'constitution',
      })
    }
  }

  // Find Roman numeral amendments ("Amendment XIV")
  ROMAN_AMENDMENT_PATTERN.lastIndex = 0
  let rMatch: RegExpExecArray | null
  while ((rMatch = ROMAN_AMENDMENT_PATTERN.exec(text)) !== null) {
    const num = ROMAN_TO_NUM[rMatch[1].toUpperCase()]
    if (num) {
      matches.push({
        start: rMatch.index,
        end: rMatch.index + rMatch[0].length,
        href: `/constitution/amendment-${num}`,
        text: rMatch[0],
        type: 'constitution',
      })
    }
  }

  // Find Article references ("Article I", "Article III")
  ARTICLE_PATTERN.lastIndex = 0
  let aMatch: RegExpExecArray | null
  while ((aMatch = ARTICLE_PATTERN.exec(text)) !== null) {
    const num = ROMAN_TO_NUM[aMatch[1].toUpperCase()]
    if (num && num <= 7) {
      matches.push({
        start: aMatch.index,
        end: aMatch.index + aMatch[0].length,
        href: `/constitution/article-${num}`,
        text: aMatch[0],
        type: 'constitution',
      })
    }
  }

  // Find named clauses ("Due Process Clause", "Commerce Clause")
  for (const clause of NAMED_CLAUSES) {
    clause.pattern.lastIndex = 0
    let cMatch: RegExpExecArray | null
    while ((cMatch = clause.pattern.exec(text)) !== null) {
      const href = clause.article
        ? `/constitution/article-${clause.article}`
        : `/constitution/amendment-${clause.amendment}`
      matches.push({
        start: cMatch.index,
        end: cMatch.index + cMatch[0].length,
        href,
        text: cMatch[0],
        type: 'constitution',
      })
    }
  }

  return matches
}

function dedupeMatches(matches: MatchInfo[]): MatchInfo[] {
  matches.sort((a, b) => a.start - b.start)
  const deduped: MatchInfo[] = []
  for (const m of matches) {
    if (deduped.length === 0 || m.start >= deduped[deduped.length - 1].end) {
      deduped.push(m)
    } else if (m.end - m.start > deduped[deduped.length - 1].end - deduped[deduped.length - 1].start) {
      deduped[deduped.length - 1] = m
    }
  }
  return deduped
}

export function parseLegalCitations(text: string): TextSegment[] {
  if (!text) return [{ text }]

  const matches = collectMatches(text)
  if (matches.length === 0) return [{ text }]

  const deduped = dedupeMatches(matches)

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

export function extractLegalTextRefs(text: string): LegalTextRef[] {
  if (!text) return []

  const matches = collectMatches(text)
  // Deduplicate by href, keeping the first label seen
  const seen = new Map<string, LegalTextRef>()
  for (const m of matches) {
    if (!seen.has(m.href)) {
      seen.set(m.href, { label: m.text, href: m.href, type: m.type })
    }
  }
  return Array.from(seen.values())
}
