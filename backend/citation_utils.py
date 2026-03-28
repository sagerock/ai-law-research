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
    "us-app-dc": "U.S. App. D.C.",
    "f-supp-2d": "F. Supp. 2d",
    "f-supp-3d": "F. Supp. 3d",
    "ohio-law-abs": "Ohio Law. Abs.",
    "cal-app-2d": "Cal. App. 2d",
    "cal-app-4th": "Cal. App. 4th",
    "cal-rptr-2d": "Cal. Rptr. 2d",
    "ohio-op-2d": "Ohio Op. 2d",
    "ohio-st3d": "Ohio St.3d",
    "ohio-st2d": "Ohio St.2d",
    "l-ed-2d": "L. Ed. 2d",
    "f-supp": "F. Supp.",
    "f-appx": "F. App'x",
    "ohio-op": "Ohio Op.",
    "cal-2d": "Cal. 2d",
    "cal-3d": "Cal. 3d",
    "cal-4th": "Cal. 4th",
    "cal-5th": "Cal. 5th",
    "so-2d": "So. 2d",
    "so-3d": "So. 3d",
    "l-ed": "L. Ed.",
    "s-ct": "S. Ct.",
    "ne2d": "N.E.2d",
    "nw2d": "N.W.2d",
    "ny2d": "N.Y.2d",
    "sw2d": "S.W.2d",
    "ad2d": "A.D.2d",
    "ad3d": "A.D.3d",
    "f4th": "F.4th",
    "f3d": "F.3d",
    "f2d": "F.2d",
    "p2d": "P.2d",
    "p3d": "P.3d",
    "a2d": "A.2d",
    "a3d": "A.3d",
    "b-r": "B.R.",
    "us": "U.S.",
    "ne": "N.E.",
    "nw": "N.W.",
    "ny": "N.Y.",
    "va": "Va.",
    "mass": "Mass.",
    "neb": "Neb.",
    "minn": "Minn.",
    "mich": "Mich.",
    "conn": "Conn.",
    "pa": "Pa.",
    "ky": "Ky.",
    "ark": "Ark.",
    "mont": "Mont.",
    "nh": "N.H.",
    "vt": "Vt.",
    "wis": "Wis.",
    "wis-2d": "Wis. 2d",
    "cal": "Cal.",
    "colo": "Colo.",
    "so": "So.",
    "f": "F.",
    "ad": "A.D.",
    "a": "A.",
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
