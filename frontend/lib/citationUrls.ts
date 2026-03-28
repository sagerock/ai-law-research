/**
 * Citation URL utilities — mirrors backend/citation_utils.py
 *
 * Generates canonical URL slugs from reporter citations and case titles.
 */

const REPORTER_TO_SLUG: Record<string, string> = {
  "U.S. App. D.C.": "us-app-dc",
  "F. Supp. 2d": "f-supp-2d",
  "F. Supp. 3d": "f-supp-3d",
  "Ohio Law. Abs.": "ohio-law-abs",
  "L. Ed. 2d": "l-ed-2d",
  "F. Supp.": "f-supp",
  "F. App'x": "f-appx",
  "Ohio Op.": "ohio-op",
  "Cal. 2d": "cal-2d",
  "Cal. 3d": "cal-3d",
  "Cal. 4th": "cal-4th",
  "Cal. 5th": "cal-5th",
  "So. 2d": "so-2d",
  "So. 3d": "so-3d",
  "L. Ed.": "l-ed",
  "S. Ct.": "s-ct",
  "N.E.2d": "ne2d",
  "N.W.2d": "nw2d",
  "N.Y.2d": "ny2d",
  "S.W.2d": "sw2d",
  "A.D.2d": "ad2d",
  "A.D.3d": "ad3d",
  "F.4th": "f4th",
  "F.3d": "f3d",
  "F.2d": "f2d",
  "P.2d": "p2d",
  "P.3d": "p3d",
  "A.2d": "a2d",
  "A.3d": "a3d",
  "B.R.": "b-r",
  "U.S.": "us",
  "N.E.": "ne",
  "N.W.": "nw",
  "N.Y.": "ny",
  "Va.": "va",
  "Mass.": "mass",
  "Neb.": "neb",
  "Minn.": "minn",
  "A.": "a",
}

function genericReporterToSlug(reporter: string): string {
  let slug = reporter.toLowerCase()
  slug = slug.replace(/'/g, "")
  slug = slug.replace(/\.(\S)/g, "$1") // "F.3d" -> "f3d"
  slug = slug.replace(/\./g, "")
  slug = slug.replace(/\s+/g, "-").trim()
  return slug
}

export function reporterCiteToSlug(cite: string): string {
  cite = cite.trim()
  const m = cite.match(/^(\d+)\s+(.+)\s+(\d+)$/)
  if (!m) {
    return cite.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")
  }
  const [, volume, reporter, page] = m
  const reporterSlug = REPORTER_TO_SLUG[reporter] ?? genericReporterToSlug(reporter)
  return `${volume}-${reporterSlug}-${page}`
}

export function caseTitleToSlug(title: string): string {
  let slug = title.toLowerCase()
  slug = slug.replace(/[^a-z0-9\s-]/g, "")
  slug = slug.replace(/\s+/g, "-").trim()
  slug = slug.replace(/-{2,}/g, "-")
  slug = slug.replace(/^-|-$/g, "")
  return slug
}

export function buildCanonicalSlug(reporterCite: string | null | undefined, title: string): string {
  if (reporterCite && reporterCite.trim()) {
    return reporterCiteToSlug(reporterCite)
  }
  return caseTitleToSlug(title)
}

export function buildCanonicalUrl(reporterCite: string | null | undefined, title: string): string {
  const slug = buildCanonicalSlug(reporterCite, title)
  return `/cases/${slug}`
}

export function buildCitationText(
  title: string,
  reporterCite: string | null | undefined,
  decisionDate: string | null | undefined,
): string {
  const year = decisionDate ? new Date(decisionDate).getFullYear() : ""
  const cite = reporterCite?.trim()
  const yearPart = year ? ` (${year})` : ""

  if (cite) {
    return `${title}, ${cite}${yearPart}`
  }
  return `${title}${yearPart}`
}
