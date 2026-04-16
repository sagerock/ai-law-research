/**
 * Citation URL utilities — mirrors backend/citation_utils.py
 *
 * Generates canonical URL slugs from reporter citations and case titles.
 */

const REPORTER_TO_SLUG: Record<string, string> = {
  "Daily Journal DAR": "daily-journal-dar",
  "Cal. App. Supp. 4th": "cal-app-supp-4th",
  "Cal. App. Supp. 2d": "cal-app-supp-2d",
  "Cal. App. Supp. 3d": "cal-app-supp-3d",
  "Am. Tribal Law": "am-tribal-law",
  "Conn. Super. Ct.": "conn-super-ct",
  "Ct. Int'l Trade": "ct-intl-trade",
  "U.S. Dist. LEXIS": "us-dist-lexis",
  "IL App (1st)": "il-app-(1st)",
  "IL App (4th)": "il-app-(4th)",
  "IL App (5th)": "il-app-(5th)",
  "Mass. App. Dec.": "mass-app-dec",
  "Mass. App. Div.": "mass-app-div",
  "Ohio Law. Abs.": "ohio-law-abs",
  "Ohio Misc. 2d": "ohio-misc-2d",
  "Ohio St. (N.S.)": "ohio-st-(ns)",
  "Serg. & Rawle": "serg-&-rawle",
  "Cal. App. 4th": "cal-app-4th",
  "Cal. Rptr. 2d": "cal-rptr-2d",
  "Cal. Rptr. 3d": "cal-rptr-3d",
  "IL App (2d)": "il-app-(2d)",
  "IL App (3d)": "il-app-(3d)",
  "Mass. App. Ct.": "mass-app-ct",
  "Mass. L. Rptr.": "mass-l-rptr",
  "Ohio App. 3d": "ohio-app-3d",
  "Cal. App. 2d": "cal-app-2d",
  "Cal. App. 3d": "cal-app-3d",
  "Colo. J. C.A.R.": "colo-j-car",
  "Hill & Den.": "hill-&-den",
  "Ill. App. 2d": "ill-app-2d",
  "Ill. App. 3d": "ill-app-3d",
  "Kan. App. 2d": "kan-app-2d",
  "Mont. LEXIS": "mont-lexis",
  "Neb. Ct. App.": "neb-ct-app",
  "NY Slip Op": "ny-slip-op",
  "Ohio Op. 2d": "ohio-op-2d",
  "Ohio St. 2d": "ohio-st-2d",
  "Ohio St. 3d": "ohio-st-3d",
  "OK CIV APP": "ok-civ-app",
  "Pa. D. & C.2d": "pa-d-&-c2d",
  "Tex. Ct. App.": "tex-ct-app",
  "Cal. Unrep.": "cal-unrep",
  "Conn. Supp.": "conn-supp",
  "F. Supp. 2d": "f-supp-2d",
  "F. Supp. 3d": "f-supp-3d",
  "N.Y. Sup. Ct.": "ny-sup-ct",
  "Ohio Misc.": "ohio-misc",
  "Ohio St.2d": "ohio-st2d",
  "Ohio St.3d": "ohio-st3d",
  "Smith & H.": "smith-&-h",
  "U.S. App. D.C.": "us-app-dc",
  "Ariz. App.": "ariz-app",
  "Charlton": "charlton",
  "Conn. App.": "conn-app",
  "Fed. Appx.": "fed-appx",
  "Mich. App.": "mich-app",
  "N.J. Super.": "nj-super",
  "Ohio App.": "ohio-app",
  "Pa. Commw.": "pa-commw",
  "Pa. D. & C.": "pa-d-&-c",
  "Pa. Super.": "pa-super",
  "Paige Ch.": "paige-ch",
  "Tenn. App.": "tenn-app",
  "U.S. LEXIS": "us-lexis",
  "Wash. App.": "wash-app",
  "Ala. App.": "ala-app",
  "Ark. App.": "ark-app",
  "Cai. Cas.": "cai-cas",
  "Cal. 4th": "cal-4th",
  "Cal. 5th": "cal-5th",
  "Cal. App.": "cal-app",
  "Connoly": "connoly",
  "Ct. Cust.": "ct-cust",
  "Cust. Ct.": "cust-ct",
  "F.Supp.2d": "fsupp2d",
  "Haw. App.": "haw-app",
  "Ill. App.": "ill-app",
  "Ind. App.": "ind-app",
  "L. Ed. 2d": "l-ed-2d",
  "Misc. 2d": "misc-2d",
  "Misc. 3d": "misc-3d",
  "N.J. Misc.": "nj-misc",
  "Ohio Op.": "ohio-op",
  "Ohio St.": "ohio-st",
  "T.C. Memo.": "tc-memo",
  "Utah 2d": "utah-2d",
  "Vet. App.": "vet-app",
  "Wash. 2d": "wash-2d",
  "App. D.C.": "app-dc",
  "Blackf.": "blackf",
  "Cal. 2d": "cal-2d",
  "Cal. 3d": "cal-3d",
  "Cal.4th": "cal4th",
  "Cal.5th": "cal5th",
  "Cranch": "cranch",
  "Del. Ch.": "del-ch",
  "F. App'x": "f-appx",
  "F. Supp.": "f-supp",
  "Fed. Cl.": "fed-cl",
  "Ga. App.": "ga-app",
  "Ill. 2d": "ill-2d",
  "La. Ann.": "la-ann",
  "Md. App.": "md-app",
  "Misc.2d": "misc2d",
  "Mo. App.": "mo-app",
  "N.C. App.": "nc-app",
  "ND App": "nd-app",
  "Or. App.": "or-app",
  "UT App": "ut-app",
  "Va. App.": "va-app",
  "Va. Cir.": "va-cir",
  "WI App": "wi-app",
  "Wis. 2d": "wis-2d",
  "Cal.2d": "cal2d",
  "Cal.3d": "cal3d",
  "Cl. Ct.": "cl-ct",
  "Ct. Cl.": "ct-cl",
  "Denio": "denio",
  "F. Cas.": "f-cas",
  "Idaho": "idaho",
  "Ill.2d": "ill2d",
  "Johns.": "johns",
  "Monag.": "monag",
  "N.J. Eq.": "nj-eq",
  "N.Y.S.2d": "nys2d",
  "OK CR": "ok-cr",
  "S.E. 2d": "se-2d",
  "So. 2d": "so-2d",
  "So. 3d": "so-3d",
  "T.C. No.": "tc-no",
  "A.D.2d": "ad2d",
  "A.D.3d": "ad3d",
  "Ariz.": "ariz",
  "Barb.": "barb",
  "C.C.P.A.": "ccpa",
  "Colo.": "colo",
  "Conn.": "conn",
  "F.4th": "f4th",
  "Iowa": "iowa",
  "L. Ed.": "l-ed",
  "Mass.": "mass",
  "Mich.": "mich",
  "Minn.": "minn",
  "Misc.": "misc",
  "Miss.": "miss",
  "Mont.": "mont",
  "NCBC": "ncbc",
  "N.E.2d": "ne2d",
  "N.E.3d": "ne3d",
  "NMCA": "nmca",
  "NMSC": "nmsc",
  "N.W.2d": "nw2d",
  "N.Y.2d": "ny2d",
  "N.Y.3d": "ny3d",
  "Ohio": "ohio",
  "Okla.": "okla",
  "Root": "root",
  "S. Ct.": "s-ct",
  "S.E.2d": "se2d",
  "So.2d": "so2d",
  "S.W.2d": "sw2d",
  "S.W.3d": "sw3d",
  "Tenn.": "tenn",
  "Utah": "utah",
  "W. Va.": "w-va",
  "Wall.": "wall",
  "Wash.": "wash",
  "Wend.": "wend",
  "A.2d": "a2d",
  "A.3d": "a3d",
  "Aik.": "aik",
  "Ala.": "ala",
  "Ark.": "ark",
  "B.R.": "b-r",
  "B.T.A.": "bta",
  "Cal.": "cal",
  "CIT": "cit",
  "C.M.A.": "cma",
  "COA": "coa",
  "Cow.": "cow",
  "D.A.R.": "dar",
  "Del.": "del",
  "F.2d": "f2d",
  "F.3d": "f3d",
  "Fla.": "fla",
  "F.R.D.": "frd",
  "Haw.": "haw",
  "How.": "how",
  "Ill.": "ill",
  "Ind.": "ind",
  "Kan.": "kan",
  "L.Ed.": "led",
  "N. C.": "n-c",
  "Neb.": "neb",
  "Nev.": "nev",
  "N.J.L.": "njl",
  "N.Y.S.": "nys",
  "P.2d": "p2d",
  "P.3d": "p3d",
  "Pet.": "pet",
  "S.C.L.": "scl",
  "S.Ct.": "sct",
  "T.C.M.": "tcm",
  "Tex.": "tex",
  "Wis.": "wis",
  "Wyo.": "wyo",
  "A.D.": "ad",
  "CO": "co",
  "D.C.": "dc",
  "Ga.": "ga",
  "IL": "il",
  "Ky.": "ky",
  "La.": "la",
  "Md.": "md",
  "Me.": "me",
  "M.J.": "mj",
  "Mo.": "mo",
  "MT": "mt",
  "N.C.": "nc",
  "N.D.": "nd",
  "N.E.": "ne",
  "N.H.": "nh",
  "N.J.": "nj",
  "N.M.": "nm",
  "NV": "nv",
  "N.W.": "nw",
  "N.Y.": "ny",
  "OK": "ok",
  "Or.": "or",
  "Pa.": "pa",
  "P.R.": "pr",
  "R.I.": "ri",
  "S.C.": "sc",
  "S.D.": "sd",
  "S.E.": "se",
  "So.": "so",
  "S.W.": "sw",
  "T.C.": "tc",
  "U.S.": "us",
  "UT": "ut",
  "Va.": "va",
  "V.I.": "vi",
  "Vt.": "vt",
  "WI": "wi",
  "WL": "wl",
  "WY": "wy",
  "A.": "a",
  "F.": "f",
  "P.": "p",
  // British reporters
  "Q.B.D.": "qbd",
  "Q.B.": "qb",
  "A.C.": "ac",
  "K.B.": "kb",
  "Ch.": "ch",
  "W.L.R.": "wlr",
  "All E.R.": "all-er",
}

function genericReporterToSlug(reporter: string): string {
  let slug = reporter.toLowerCase()
  slug = slug.replace(/'/g, "")
  slug = slug.replace(/\.(\S)/g, "$1") // "F.3d" -> "f3d"
  slug = slug.replace(/\./g, "")
  slug = slug.replace(/\s+/g, "-").trim()
  return slug
}

function normalizeCite(cite: string): string {
  // Take only the first citation if comma-separated
  cite = cite.split(",")[0].trim()
  // Strip trailing parenthetical (year, court info, etc.)
  cite = cite.replace(/\s*\([^)]*\)\s*$/, "").trim()
  return cite
}

export function reporterCiteToSlug(cite: string): string | null {
  cite = normalizeCite(cite)
  const m = cite.match(/^(\d+)\s+(.+)\s+(\d+)$/)
  if (!m) {
    return null
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
    const slug = reporterCiteToSlug(reporterCite)
    if (slug) return slug
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
