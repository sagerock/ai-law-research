"""
Citation URL utilities — bidirectional mapping between legal reporter citations
and URL-safe slugs.

Examples:
    "550 U.S. 544"           <-> "550-us-544"
    "103 F.3d 144"           <-> "103-f3d-144"
    "121 U.S. App. D.C. 315" <-> "121-us-app-dc-315"
"""

import re
from typing import Optional, Tuple

# Canonical mapping: slug fragment -> DB reporter format
# Ordered longest-first so greedy matching works correctly
SLUG_TO_REPORTER: dict[str, str] = {
    "daily-journal-dar": "Daily Journal DAR",
    "cal-app-supp-4th": "Cal. App. Supp. 4th",
    "cal-app-supp-2d": "Cal. App. Supp. 2d",
    "cal-app-supp-3d": "Cal. App. Supp. 3d",
    "am-tribal-law": "Am. Tribal Law",
    "conn-super-ct": "Conn. Super. Ct.",
    "ct-intl-trade": "Ct. Int'l Trade",
    "us-dist-lexis": "U.S. Dist. LEXIS",
    "il-app-(1st)": "IL App (1st)",
    "il-app-(4th)": "IL App (4th)",
    "il-app-(5th)": "IL App (5th)",
    "mass-app-dec": "Mass. App. Dec.",
    "mass-app-div": "Mass. App. Div.",
    "ohio-law-abs": "Ohio Law. Abs.",
    "ohio-misc-2d": "Ohio Misc. 2d",
    "ohio-st-(ns)": "Ohio St. (N.S.)",
    "serg-&-rawle": "Serg. & Rawle",
    "cal-app-4th": "Cal. App. 4th",
    "cal-rptr-2d": "Cal. Rptr. 2d",
    "cal-rptr-3d": "Cal. Rptr. 3d",
    "il-app-(2d)": "IL App (2d)",
    "il-app-(3d)": "IL App (3d)",
    "mass-app-ct": "Mass. App. Ct.",
    "mass-l-rptr": "Mass. L. Rptr.",
    "ohio-app-3d": "Ohio App. 3d",
    "cal-app-2d": "Cal. App. 2d",
    "cal-app-3d": "Cal. App. 3d",
    "colo-j-car": "Colo. J. C.A.R.",
    "hill-&-den": "Hill & Den.",
    "ill-app-2d": "Ill. App. 2d",
    "ill-app-3d": "Ill. App. 3d",
    "kan-app-2d": "Kan. App. 2d",
    "mont-lexis": "Mont. LEXIS",
    "neb-ct-app": "Neb. Ct. App.",
    "ny-slip-op": "NY Slip Op",
    "ohio-op-2d": "Ohio Op. 2d",
    "ohio-st-2d": "Ohio St. 2d",
    "ohio-st-3d": "Ohio St. 3d",
    "ok-civ-app": "OK CIV APP",
    "pa-d-&-c2d": "Pa. D. & C.2d",
    "tex-ct-app": "Tex. Ct. App.",
    "cal-unrep": "Cal. Unrep.",
    "conn-supp": "Conn. Supp.",
    "f-supp-2d": "F. Supp. 2d",
    "f-supp-3d": "F. Supp. 3d",
    "ny-sup-ct": "N.Y. Sup. Ct.",
    "ohio-misc": "Ohio Misc.",
    "ohio-st2d": "Ohio St.2d",
    "ohio-st3d": "Ohio St.3d",
    "smith-&-h": "Smith & H.",
    "us-app-dc": "U.S. App. D.C.",
    "ariz-app": "Ariz. App.",
    "charlton": "Charlton",
    "conn-app": "Conn. App.",
    "fed-appx": "Fed. Appx.",
    "mich-app": "Mich. App.",
    "nj-super": "N.J. Super.",
    "ohio-app": "Ohio App.",
    "pa-commw": "Pa. Commw.",
    "pa-d-&-c": "Pa. D. & C.",
    "pa-super": "Pa. Super.",
    "paige-ch": "Paige Ch.",
    "tenn-app": "Tenn. App.",
    "us-lexis": "U.S. LEXIS",
    "wash-app": "Wash. App.",
    "ala-app": "Ala. App.",
    "ark-app": "Ark. App.",
    "cai-cas": "Cai. Cas.",
    "cal-4th": "Cal. 4th",
    "cal-5th": "Cal. 5th",
    "cal-app": "Cal. App.",
    "connoly": "Connoly",
    "ct-cust": "Ct. Cust.",
    "cust-ct": "Cust. Ct.",
    "fsupp2d": "F.Supp.2d",
    "haw-app": "Haw. App.",
    "ill-app": "Ill. App.",
    "ind-app": "Ind. App.",
    "l-ed-2d": "L. Ed. 2d",
    "misc-2d": "Misc. 2d",
    "misc-3d": "Misc. 3d",
    "nj-misc": "N.J. Misc.",
    "ohio-op": "Ohio Op.",
    "ohio-st": "Ohio St.",
    "tc-memo": "T.C. Memo.",
    "utah-2d": "Utah 2d",
    "vet-app": "Vet. App.",
    "wash-2d": "Wash. 2d",
    "app-dc": "App. D.C.",
    "blackf": "Blackf.",
    "cal-2d": "Cal. 2d",
    "cal-3d": "Cal. 3d",
    "cal4th": "Cal.4th",
    "cal5th": "Cal.5th",
    "cranch": "Cranch",
    "del-ch": "Del. Ch.",
    "f-appx": "F. App'x",
    "f-supp": "F. Supp.",
    "fed-cl": "Fed. Cl.",
    "ga-app": "Ga. App.",
    "ill-2d": "Ill. 2d",
    "la-ann": "La. Ann.",
    "md-app": "Md. App.",
    "misc2d": "Misc.2d",
    "mo-app": "Mo. App.",
    "nc-app": "N.C. App.",
    "nd-app": "ND App",
    "or-app": "Or. App.",
    "ut-app": "UT App",
    "va-app": "Va. App.",
    "va-cir": "Va. Cir.",
    "wi-app": "WI App",
    "wis-2d": "Wis. 2d",
    "cal2d": "Cal.2d",
    "cal3d": "Cal.3d",
    "cl-ct": "Cl. Ct.",
    "ct-cl": "Ct. Cl.",
    "denio": "Denio",
    "f-cas": "F. Cas.",
    "idaho": "Idaho",
    "ill2d": "Ill.2d",
    "johns": "Johns.",
    "monag": "Monag.",
    "nj-eq": "N.J. Eq.",
    "nys2d": "N.Y.S.2d",
    "ok-cr": "OK CR",
    "se-2d": "S.E. 2d",
    "so-2d": "So. 2d",
    "so-3d": "So. 3d",
    "tc-no": "T.C. No.",
    "ad2d": "A.D.2d",
    "ad3d": "A.D.3d",
    "ariz": "Ariz.",
    "barb": "Barb.",
    "ccpa": "C.C.P.A.",
    "colo": "Colo.",
    "conn": "Conn.",
    "f4th": "F.4th",
    "iowa": "Iowa",
    "l-ed": "L. Ed.",
    "mass": "Mass.",
    "mich": "Mich.",
    "minn": "Minn.",
    "misc": "Misc.",
    "miss": "Miss.",
    "mont": "Mont.",
    "ncbc": "NCBC",
    "ne2d": "N.E.2d",
    "ne3d": "N.E.3d",
    "nmca": "NMCA",
    "nmsc": "NMSC",
    "nw2d": "N.W.2d",
    "ny2d": "N.Y.2d",
    "ny3d": "N.Y.3d",
    "ohio": "Ohio",
    "okla": "Okla.",
    "root": "Root",
    "s-ct": "S. Ct.",
    "se2d": "S.E.2d",
    "so2d": "So.2d",
    "sw2d": "S.W.2d",
    "sw3d": "S.W.3d",
    "tenn": "Tenn.",
    "utah": "Utah",
    "w-va": "W. Va.",
    "wall": "Wall.",
    "wash": "Wash.",
    "wend": "Wend.",
    "a2d": "A.2d",
    "a3d": "A.3d",
    "aik": "Aik.",
    "ala": "Ala.",
    "ark": "Ark.",
    "b-r": "B.R.",
    "bta": "B.T.A.",
    "cal": "Cal.",
    "cit": "CIT",
    "cma": "C.M.A.",
    "coa": "COA",
    "cow": "Cow.",
    "dar": "D.A.R.",
    "del": "Del.",
    "f2d": "F.2d",
    "f3d": "F.3d",
    "fla": "Fla.",
    "frd": "F.R.D.",
    "haw": "Haw.",
    "how": "How.",
    "ill": "Ill.",
    "ind": "Ind.",
    "kan": "Kan.",
    "led": "L.Ed.",
    "n-c": "N. C.",
    "neb": "Neb.",
    "nev": "Nev.",
    "njl": "N.J.L.",
    "nys": "N.Y.S.",
    "p2d": "P.2d",
    "p3d": "P.3d",
    "pet": "Pet.",
    "scl": "S.C.L.",
    "sct": "S.Ct.",
    "tcm": "T.C.M.",
    "tex": "Tex.",
    "wis": "Wis.",
    "wyo": "Wyo.",
    "ad": "A.D.",
    "co": "CO",
    "dc": "D.C.",
    "ga": "Ga.",
    "il": "IL",
    "ky": "Ky.",
    "la": "La.",
    "md": "Md.",
    "me": "Me.",
    "mj": "M.J.",
    "mo": "Mo.",
    "mt": "MT",
    "nc": "N.C.",
    "nd": "N.D.",
    "ne": "N.E.",
    "nh": "N.H.",
    "nj": "N.J.",
    "nm": "N.M.",
    "nv": "NV",
    "nw": "N.W.",
    "ny": "N.Y.",
    "ok": "OK",
    "or": "Or.",
    "pa": "Pa.",
    "pr": "P.R.",
    "ri": "R.I.",
    "sc": "S.C.",
    "sd": "S.D.",
    "se": "S.E.",
    "so": "So.",
    "sw": "S.W.",
    "tc": "T.C.",
    "us": "U.S.",
    "ut": "UT",
    "va": "Va.",
    "vi": "V.I.",
    "vt": "Vt.",
    "wi": "WI",
    "wl": "WL",
    "wy": "WY",
    "a": "A.",
    "f": "F.",
    "p": "P.",
}

# Reverse mapping: DB reporter format -> slug fragment
REPORTER_TO_SLUG: dict[str, str] = {v: k for k, v in SLUG_TO_REPORTER.items()}


def _generic_reporter_to_slug(reporter: str) -> str:
    """Fallback for reporters not in the lookup table."""
    slug = reporter.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"\.(\S)", r"\1", slug)  # "F.3d" -> "f3d" (period before non-space)
    slug = slug.replace(".", "")
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def _generic_slug_to_reporter(slug: str) -> str:
    """Best-effort reverse for unknown reporter slugs. Not guaranteed to match DB."""
    return slug.upper().replace("-", " ")


def reporter_cite_to_slug(cite: str) -> str:
    """Convert a full reporter citation to a URL slug.

    "550 U.S. 544" -> "550-us-544"
    """
    cite = cite.strip()
    # Extract leading volume number
    m = re.match(r"^(\d+)\s+(.+)\s+(\d+)$", cite)
    if not m:
        # Fallback: just slugify the whole thing
        return re.sub(r"[^a-z0-9]+", "-", cite.lower()).strip("-")

    volume, reporter, page = m.group(1), m.group(2), m.group(3)
    reporter_slug = REPORTER_TO_SLUG.get(reporter, _generic_reporter_to_slug(reporter))
    return f"{volume}-{reporter_slug}-{page}"


def slug_to_reporter_cite(slug: str) -> Optional[str]:
    """Convert a URL slug back to a reporter citation string.

    "550-us-544" -> "550 U.S. 544"
    Returns None if the slug doesn't match a citation pattern.
    """
    parsed = parse_citation_slug(slug)
    if parsed is None:
        return None
    volume, reporter, page = parsed
    return f"{volume} {reporter} {page}"


def parse_citation_slug(slug: str) -> Optional[Tuple[str, str, str]]:
    """Parse a slug into (volume, reporter_display, page) or None.

    Tries known reporter slugs longest-first, then falls back to generic parsing.
    """
    # Pure numeric = legacy case ID, not a citation
    if slug.isdigit():
        return None

    # Must start with a number (volume)
    m = re.match(r"^(\d+)-(.+)-(\d+)$", slug)
    if not m:
        return None

    volume = m.group(1)
    middle = m.group(2)  # reporter slug portion
    page = m.group(3)

    # Try known reporters, longest slug first (already ordered in SLUG_TO_REPORTER)
    for reporter_slug, reporter_display in SLUG_TO_REPORTER.items():
        if middle == reporter_slug:
            return (volume, reporter_display, page)

    # The greedy regex above grabbed the LAST number as page.
    # For unknown reporters, accept whatever the middle is.
    reporter_display = _generic_slug_to_reporter(middle)
    return (volume, reporter_display, page)


def case_title_to_slug(title: str) -> str:
    """Convert a case title to a URL-safe slug.

    "Bell Atlantic Corp. v. Twombly" -> "bell-atlantic-corp-v-twombly"
    """
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)  # keep only alphanum, spaces, hyphens
    slug = re.sub(r"\s+", "-", slug.strip())   # spaces to hyphens
    slug = re.sub(r"-{2,}", "-", slug)         # collapse multiple hyphens
    slug = slug.strip("-")
    return slug


def build_canonical_slug(reporter_cite: Optional[str], title: str) -> str:
    """Build the canonical URL slug for a case.

    Prefers reporter citation; falls back to title slug.
    """
    if reporter_cite and reporter_cite.strip():
        return reporter_cite_to_slug(reporter_cite)
    return case_title_to_slug(title)
