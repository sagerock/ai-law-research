# Citation-Native URLs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace opaque `/case/{id}` URLs with citation-native `/cases/{volume}-{reporter}-{page}` URLs, making lawstudygroup.com the open citation layer for American case law.

**Architecture:** New backend resolver endpoint translates citation slugs to case IDs. New frontend catch-all route at `/cases/[...slug]` handles citation URLs with SSR. Old `/case/[id]` route 301-redirects to canonical citation URLs. Reporter normalization is a standalone testable module shared between Python and TypeScript.

**Tech Stack:** Python (FastAPI/asyncpg), TypeScript (Next.js 16 App Router), PostgreSQL

**Spec:** `docs/superpowers/specs/2026-03-28-citation-native-urls-design.md`

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/citation_utils.py` | **New** — Reporter normalization table, slug↔citation parsing, slug generation from case data |
| `backend/test_citation_utils.py` | **New** — Tests for all citation_utils functions |
| `backend/main.py` | **Modify** — Add `GET /api/v1/cases/resolve/{slug}` endpoint, update sitemap endpoint to include `reporter_cite` |
| `frontend/lib/citationUrls.ts` | **New** — TypeScript mirror of reporter normalization + URL generation |
| `frontend/app/cases/[...slug]/page.tsx` | **New** — Citation URL route with SSR, metadata, canonical link |
| `frontend/app/case/[id]/page.tsx` | **Modify** — 301 redirect to canonical citation URL |
| `frontend/app/case/[id]/CaseDetailClient.tsx` | **Modify** — Update "Copy Citation" button to include permalink |
| `frontend/app/sitemap.ts` | **Modify** — Use citation slugs instead of case IDs |

---

### Task 1: Backend Citation Utils — Reporter Normalization

**Files:**
- Create: `backend/citation_utils.py`
- Create: `backend/test_citation_utils.py`

- [ ] **Step 1: Write failing tests for reporter normalization**

Create `backend/test_citation_utils.py`:

```python
import pytest
from citation_utils import (
    reporter_cite_to_slug,
    slug_to_reporter_cite,
    parse_citation_slug,
    case_title_to_slug,
    build_canonical_slug,
)


class TestReporterCiteToSlug:
    def test_us_reports(self):
        assert reporter_cite_to_slug("550 U.S. 544") == "550-us-544"

    def test_federal_reporter_2d(self):
        assert reporter_cite_to_slug("457 F.2d 365") == "457-f2d-365"

    def test_federal_reporter_3d(self):
        assert reporter_cite_to_slug("103 F.3d 144") == "103-f3d-144"

    def test_federal_reporter_4th(self):
        assert reporter_cite_to_slug("12 F.4th 100") == "12-f4th-100"

    def test_federal_appendix(self):
        assert reporter_cite_to_slug("206 F. App'x 317") == "206-f-appx-317"

    def test_federal_supplement(self):
        assert reporter_cite_to_slug("100 F. Supp. 200") == "100-f-supp-200"

    def test_federal_supplement_2d(self):
        assert reporter_cite_to_slug("100 F. Supp. 2d 200") == "100-f-supp-2d-200"

    def test_cal_2d(self):
        assert reporter_cite_to_slug("51 Cal. 2d 409") == "51-cal-2d-409"

    def test_ne(self):
        assert reporter_cite_to_slug("118 N.E. 1082") == "118-ne-1082"

    def test_ne2d(self):
        assert reporter_cite_to_slug("100 N.E.2d 50") == "100-ne2d-50"

    def test_ny(self):
        assert reporter_cite_to_slug("124 N.Y. 538") == "124-ny-538"

    def test_ny2d(self):
        assert reporter_cite_to_slug("50 N.Y.2d 100") == "50-ny2d-100"

    def test_us_app_dc(self):
        assert reporter_cite_to_slug("121 U.S. App. D.C. 315") == "121-us-app-dc-315"

    def test_s_ct(self):
        assert reporter_cite_to_slug("100 S. Ct. 200") == "100-s-ct-200"

    def test_l_ed(self):
        assert reporter_cite_to_slug("100 L. Ed. 200") == "100-l-ed-200"

    def test_l_ed_2d(self):
        assert reporter_cite_to_slug("100 L. Ed. 2d 200") == "100-l-ed-2d-200"

    def test_bankruptcy_reporter(self):
        assert reporter_cite_to_slug("100 B.R. 200") == "100-b-r-200"

    def test_p2d(self):
        assert reporter_cite_to_slug("474 P.2d 689") == "474-p2d-689"

    def test_so_2d(self):
        assert reporter_cite_to_slug("100 So. 2d 200") == "100-so-2d-200"

    def test_sw2d(self):
        assert reporter_cite_to_slug("100 S.W.2d 200") == "100-sw2d-200"

    def test_ohio_op(self):
        assert reporter_cite_to_slug("11 Ohio Op. 246") == "11-ohio-op-246"

    def test_a2d(self):
        assert reporter_cite_to_slug("100 A.2d 200") == "100-a2d-200"

    def test_va(self):
        assert reporter_cite_to_slug("196 Va. 493") == "196-va-493"

    def test_mass(self):
        assert reporter_cite_to_slug("100 Mass. 200") == "100-mass-200"


class TestSlugToReporterCite:
    def test_us(self):
        assert slug_to_reporter_cite("550-us-544") == "550 U.S. 544"

    def test_f3d(self):
        assert slug_to_reporter_cite("103-f3d-144") == "103 F.3d 144"

    def test_f_appx(self):
        assert slug_to_reporter_cite("206-f-appx-317") == "206 F. App'x 317"

    def test_cal_2d(self):
        assert slug_to_reporter_cite("51-cal-2d-409") == "51 Cal. 2d 409"

    def test_us_app_dc(self):
        assert slug_to_reporter_cite("121-us-app-dc-315") == "121 U.S. App. D.C. 315"

    def test_l_ed_2d(self):
        assert slug_to_reporter_cite("100-l-ed-2d-200") == "100 L. Ed. 2d 200"


class TestParseCitationSlug:
    """parse_citation_slug returns (volume, reporter_cite, page) or None"""

    def test_simple_citation(self):
        assert parse_citation_slug("550-us-544") == ("550", "U.S.", "544")

    def test_multi_part_reporter(self):
        assert parse_citation_slug("121-us-app-dc-315") == ("121", "U.S. App. D.C.", "315")

    def test_not_a_citation(self):
        assert parse_citation_slug("wood-v-lucy-lady-duff-gordon") is None

    def test_pure_number(self):
        assert parse_citation_slug("145730") is None


class TestCaseTitleToSlug:
    def test_basic(self):
        assert case_title_to_slug("Bell Atlantic Corp. v. Twombly") == "bell-atlantic-corp-v-twombly"

    def test_with_comma(self):
        assert case_title_to_slug("Wood v. . Lucy, Lady Duff-Gordon") == "wood-v-lucy-lady-duff-gordon"

    def test_strips_leading_trailing_hyphens(self):
        slug = case_title_to_slug("  Erie Railroad Co. v. Tompkins  ")
        assert not slug.startswith("-")
        assert not slug.endswith("-")

    def test_collapses_multiple_hyphens(self):
        slug = case_title_to_slug("Hamer v. . Sidway")
        assert "--" not in slug


class TestBuildCanonicalSlug:
    def test_with_reporter_cite(self):
        assert build_canonical_slug("550 U.S. 544", "Bell Atlantic Corp. v. Twombly") == "550-us-544"

    def test_without_reporter_cite(self):
        assert build_canonical_slug(None, "Wood v. Lucy, Lady Duff-Gordon") == "wood-v-lucy-lady-duff-gordon"

    def test_empty_reporter_cite(self):
        assert build_canonical_slug("", "Wood v. Lucy, Lady Duff-Gordon") == "wood-v-lucy-lady-duff-gordon"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test_citation_utils.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'citation_utils'`

- [ ] **Step 3: Implement citation_utils.py**

Create `backend/citation_utils.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test_citation_utils.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/citation_utils.py backend/test_citation_utils.py
git commit -m "feat: add citation URL utilities with reporter normalization"
```

---

### Task 2: Backend Resolver Endpoint

**Files:**
- Modify: `backend/main.py` (add endpoint near line 917, before existing case endpoints)

- [ ] **Step 1: Write failing test for the resolver endpoint**

Append to `backend/test_citation_utils.py`:

```python
import pytest


# --- Integration tests for resolve endpoint ---
# These test the endpoint logic functions, not the HTTP layer.
# The actual endpoint wires these to asyncpg.

class TestResolveSlugLogic:
    """Test the slug resolution priority logic."""

    def test_pure_numeric_is_legacy_id(self):
        """Pure numbers should be treated as legacy case IDs, not citations."""
        assert parse_citation_slug("145730") is None

    def test_citation_slug_parses(self):
        result = parse_citation_slug("550-us-544")
        assert result == ("550", "U.S.", "544")

    def test_name_slug_does_not_parse_as_citation(self):
        assert parse_citation_slug("bell-atlantic-corp-v-twombly") is None

    def test_roundtrip_cite_to_slug_to_cite(self):
        """reporter_cite -> slug -> reporter_cite should roundtrip."""
        original = "550 U.S. 544"
        slug = reporter_cite_to_slug(original)
        restored = slug_to_reporter_cite(slug)
        assert restored == original

    def test_roundtrip_f3d(self):
        original = "103 F.3d 144"
        slug = reporter_cite_to_slug(original)
        restored = slug_to_reporter_cite(slug)
        assert restored == original
```

- [ ] **Step 2: Run tests to verify they pass** (these test existing functions)

Run: `cd backend && python -m pytest test_citation_utils.py -v`
Expected: All PASS

- [ ] **Step 3: Add the resolve endpoint to main.py**

Add this before the existing `@app.get("/api/v1/cases/{case_id}")` endpoint (around line 916 in `backend/main.py`). It must come before the `{case_id}` route so FastAPI matches it first:

```python
from citation_utils import parse_citation_slug, slug_to_reporter_cite, case_title_to_slug, build_canonical_slug
from fastapi.responses import JSONResponse

@app.get("/api/v1/cases/resolve/{slug:path}")
async def resolve_case_slug(slug: str):
    """Resolve a citation slug or name slug to a case ID and canonical slug.

    Priority:
    1. Pure numeric string -> legacy case ID lookup
    2. Citation pattern (e.g., 550-us-544) -> reporter_cite lookup
    3. Name slug (e.g., bell-atlantic-corp-v-twombly) -> title match
    """
    async with db_pool.acquire() as conn:
        # 1. Pure numeric -> legacy case ID
        if slug.isdigit():
            row = await conn.fetchrow(
                "SELECT id, reporter_cite, title FROM cases WHERE id = $1",
                slug,
            )
            if row:
                canonical = build_canonical_slug(row["reporter_cite"], row["title"])
                return JSONResponse(
                    content={"case_id": row["id"], "canonical_slug": canonical},
                    headers={"Cache-Control": "public, max-age=86400"},
                )
            raise HTTPException(status_code=404, detail="Case not found")

        # 2. Try as citation slug
        parsed = parse_citation_slug(slug)
        if parsed:
            volume, reporter, page = parsed
            cite_str = f"{volume} {reporter} {page}"
            row = await conn.fetchrow(
                "SELECT id, reporter_cite, title FROM cases WHERE reporter_cite = $1",
                cite_str,
            )
            if row:
                canonical = build_canonical_slug(row["reporter_cite"], row["title"])
                return JSONResponse(
                    content={"case_id": row["id"], "canonical_slug": canonical},
                    headers={"Cache-Control": "public, max-age=86400"},
                )

        # 3. Try as name slug
        # Query all cases and match by slugified title
        # TODO: At 500k+ cases, add a materialized title_slug column instead
        rows = await conn.fetch(
            "SELECT id, reporter_cite, title FROM cases WHERE title IS NOT NULL"
        )
        for row in rows:
            if case_title_to_slug(row["title"]) == slug:
                canonical = build_canonical_slug(row["reporter_cite"], row["title"])
                return JSONResponse(
                    content={"case_id": row["id"], "canonical_slug": canonical},
                    headers={"Cache-Control": "public, max-age=86400"},
                )

    raise HTTPException(status_code=404, detail="Case not found")
```

- [ ] **Step 4: Add the import at the top of main.py**

Near the other imports at the top of `backend/main.py` (after `from uuid import UUID`), add:

```python
from citation_utils import parse_citation_slug, slug_to_reporter_cite, case_title_to_slug, build_canonical_slug
```

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/test_citation_utils.py
git commit -m "feat: add case slug resolver endpoint"
```

---

### Task 3: Update Backend Sitemap Endpoint

**Files:**
- Modify: `backend/main.py:1806-1826` (the `get_sitemap_cases` function)

- [ ] **Step 1: Update the sitemap endpoint to include reporter_cite**

Replace the existing `get_sitemap_cases` function at line 1806 of `backend/main.py`:

```python
@app.get("/api/v1/sitemap/cases")
async def get_sitemap_cases():
    """Get all case IDs, titles, and citation slugs for sitemap generation"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, decision_date, reporter_cite
            FROM cases
            ORDER BY decision_date DESC NULLS LAST
        """)

    return {
        "cases": [
            {
                "id": row["id"],
                "title": row["title"],
                "date": row["decision_date"].isoformat() if row["decision_date"] else None,
                "reporter_cite": row["reporter_cite"],
                "canonical_slug": build_canonical_slug(row["reporter_cite"], row["title"]),
            }
            for row in rows
        ],
        "count": len(rows)
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "feat: include canonical_slug in sitemap endpoint"
```

---

### Task 4: Frontend Citation URL Utilities

**Files:**
- Create: `frontend/lib/citationUrls.ts`

- [ ] **Step 1: Create the TypeScript citation URL module**

Create `frontend/lib/citationUrls.ts`:

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/lib/citationUrls.ts
git commit -m "feat: add TypeScript citation URL utilities"
```

---

### Task 5: New Frontend Citation URL Route

**Files:**
- Create: `frontend/app/cases/[...slug]/page.tsx`

- [ ] **Step 1: Create the citation URL route**

Create `frontend/app/cases/[...slug]/page.tsx`:

```tsx
import { Metadata } from 'next'
import { notFound, redirect } from 'next/navigation'
import CaseDetailClient, { CaseDetail } from '../../case/[id]/CaseDetailClient'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://lawstudygroup.com'

interface ResolveResult {
  case_id: string
  canonical_slug: string
}

interface PageProps {
  params: Promise<{ slug: string[] }>
}

async function resolveSlug(slug: string): Promise<ResolveResult | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/resolve/${slug}`, {
      next: { revalidate: 86400 } // Cache resolve for 24h — citations are immutable
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

async function getCase(id: string): Promise<CaseDetail | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/${id}`, {
      next: { revalidate: 3600 }
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const slugStr = slug.join('/')
  const resolved = await resolveSlug(slugStr)
  if (!resolved) return { title: 'Case Not Found' }

  const caseData = await getCase(resolved.case_id)
  if (!caseData) return { title: 'Case Not Found' }

  const caseName = caseData.title || caseData.case_name || 'Unknown Case'
  const court = caseData.court_name || ''
  const dateStr = caseData.decision_date || caseData.date_filed
  const year = dateStr ? new Date(dateStr).getFullYear() : ''
  const canonicalUrl = `${SITE_URL}/cases/${resolved.canonical_slug}`

  return {
    title: caseName,
    description: `Read the full case brief for ${caseName}${court ? ` (${court}${year ? `, ${year}` : ''})` : ''}. Free case briefs for law students.`,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: `${caseName} | Law Study Group`,
      description: `Case brief for ${caseName}`,
      type: 'article',
      url: canonicalUrl,
    },
  }
}

export default async function CitationCasePage({ params }: PageProps) {
  const { slug } = await params
  const slugStr = slug.join('/')

  const resolved = await resolveSlug(slugStr)
  if (!resolved) notFound()

  // Redirect to canonical slug if URL doesn't match
  if (slugStr !== resolved.canonical_slug) {
    redirect(`/cases/${resolved.canonical_slug}`)
  }

  const caseData = await getCase(resolved.case_id)
  if (!caseData) notFound()

  return <CaseDetailClient caseData={caseData} caseId={resolved.case_id} />
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/cases/\[\...slug\]/page.tsx
git commit -m "feat: add citation-native URL route with SSR and canonical tags"
```

---

### Task 6: Redirect Old `/case/[id]` Route

**Files:**
- Modify: `frontend/app/case/[id]/page.tsx`

- [ ] **Step 1: Update the old route to 301 redirect**

Replace the entire contents of `frontend/app/case/[id]/page.tsx`:

```tsx
import { permanentRedirect } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PageProps {
  params: Promise<{ id: string }>
}

async function resolveSlug(slug: string): Promise<{ case_id: string; canonical_slug: string } | null> {
  try {
    const response = await fetch(`${API_URL}/api/v1/cases/resolve/${slug}`, {
      next: { revalidate: 86400 }
    })
    if (!response.ok) return null
    return response.json()
  } catch {
    return null
  }
}

export default async function CaseRedirectPage({ params }: PageProps) {
  const { id } = await params

  const resolved = await resolveSlug(id)
  if (!resolved) {
    // Fallback: try the old route directly in case resolve fails
    permanentRedirect(`/cases/${id}`)
  }

  permanentRedirect(`/cases/${resolved.canonical_slug}`)
}
```

Note: `permanentRedirect` from Next.js sends a 308 (permanent redirect), preserving SEO link equity from old `/case/{id}` URLs.

- [ ] **Step 2: Commit**

```bash
git add frontend/app/case/\[id\]/page.tsx
git commit -m "feat: 301 redirect old /case/{id} URLs to canonical citation URLs"
```

---

### Task 7: Update "Copy Citation" Button with Permalink

**Files:**
- Modify: `frontend/app/case/[id]/CaseDetailClient.tsx` (the `handleCopyCitation` function around line 406)

- [ ] **Step 1: Update the handleCopyCitation function**

In `frontend/app/case/[id]/CaseDetailClient.tsx`, add the import at the top (after other imports):

```typescript
import { buildCanonicalUrl, buildCitationText } from '@/lib/citationUrls'
```

Then replace the `handleCopyCitation` function (lines 406-416):

```typescript
  const handleCopyCitation = () => {
    if (caseData) {
      const caseName = caseData.title || caseData.case_name || 'Unknown Case'
      const dateStr = caseData.decision_date || caseData.date_filed
      const reporterCite = caseData.metadata?.reporter_cite || (caseData as any).reporter_cite
      const citationLine = buildCitationText(caseName, reporterCite, dateStr)
      const canonicalPath = buildCanonicalUrl(reporterCite, caseName)
      const fullUrl = `https://lawstudygroup.com${canonicalPath}`
      navigator.clipboard.writeText(`${citationLine}\n${fullUrl}`)
      setCopiedCitation(true)
      setTimeout(() => setCopiedCitation(false), 2000)
    }
  }
```

- [ ] **Step 2: Verify `reporter_cite` is available in the case data**

The backend `SELECT c.*` already returns `reporter_cite` from the `cases` table. Verify by checking the `CaseDetail` interface in `CaseDetailClient.tsx` and add `reporter_cite` if missing:

In the `CaseDetail` interface (around line 14), add:

```typescript
  reporter_cite?: string
```

- [ ] **Step 3: Commit**

```bash
git add frontend/app/case/\[id\]/CaseDetailClient.tsx
git commit -m "feat: copy citation button now includes permalink URL"
```

---

### Task 8: Update Sitemap to Use Citation Slugs

**Files:**
- Modify: `frontend/app/sitemap.ts`

- [ ] **Step 1: Update sitemap to use canonical slugs**

Replace the contents of `frontend/app/sitemap.ts`:

```typescript
import { MetadataRoute } from 'next'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://lawstudygroup.com'

interface CaseForSitemap {
  id: string
  title: string
  date: string | null
  reporter_cite: string | null
  canonical_slug: string
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: SITE_URL,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${SITE_URL}/transparency`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${SITE_URL}/briefcheck`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.7,
    },
  ]

  try {
    const response = await fetch(`${API_URL}/api/v1/sitemap/cases`, {
      next: { revalidate: 3600 }
    })

    if (!response.ok) {
      console.error('Failed to fetch cases for sitemap')
      return staticPages
    }

    const data = await response.json()
    const cases: CaseForSitemap[] = data.cases || []

    const casePages: MetadataRoute.Sitemap = cases.map((c) => ({
      url: `${SITE_URL}/cases/${c.canonical_slug}`,
      lastModified: c.date ? new Date(c.date) : new Date(),
      changeFrequency: 'monthly' as const,
      priority: 0.6,
    }))

    return [...staticPages, ...casePages]
  } catch (error) {
    console.error('Error generating sitemap:', error)
    return staticPages
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/sitemap.ts
git commit -m "feat: sitemap now uses canonical citation URLs"
```

---

### Task 9: Update Internal Links Across Frontend

**Files:**
- Modify: Various frontend files that link to `/case/{id}`

- [ ] **Step 1: Find all internal case links**

Run: `grep -rn "'/case/" frontend/app/ frontend/components/ frontend/lib/ --include="*.tsx" --include="*.ts" | grep -v node_modules`

This will show all places that generate `/case/{id}` links. Common patterns to update:

- `href={/case/${id}}` → use `buildCanonicalUrl(reporter_cite, title)` or keep as `/case/${id}` (the 301 redirect handles it)

For v1, the 301 redirect from `/case/{id}` covers all existing internal links automatically. However, to avoid unnecessary redirects on navigation, update the most-used link sources:

In search results (`frontend/app/page.tsx`), collection pages, and library pages, update case links from:
```tsx
href={`/case/${case.id}`}
```
to:
```tsx
href={`/cases/${case.canonical_slug || case.id}`}
```

This requires the search API and collection APIs to also return `reporter_cite` (which they already do via `SELECT c.*`). The frontend can compute the slug client-side using `buildCanonicalUrl`.

- [ ] **Step 2: Commit**

```bash
git add frontend/
git commit -m "feat: update internal case links to use citation URLs"
```

---

### Task 10: Update CLAUDE.md Site Name

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update branding references**

In `CLAUDE.md`, update the branding section:

Replace:
```markdown
**Sage's Study Group** - A free alternative to Quimbee
```
with:
```markdown
**Law Study Group** - A free alternative to Quimbee
```

Replace:
```markdown
- Site name: "Sage's Study Group"
- Tagline: "Free AI Case Briefs for Law Students"
- HTML title: "Sage's Study Group | Free AI Case Briefs for Law Students"
```
with:
```markdown
- Site name: "Law Study Group"
- Tagline: "Free AI Case Briefs for Law Students"
- HTML title: "Law Study Group | Free AI Case Briefs for Law Students"
```

Also update the Open Graph title reference in the metadata section if present.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update site name from Sage's Study Group to Law Study Group"
```

---

## Task Dependency Order

```
Task 1 (citation_utils.py)
    ↓
Task 2 (resolver endpoint)  →  Task 3 (sitemap endpoint)
    ↓                              ↓
Task 4 (TS citationUrls)    Task 8 (sitemap frontend)
    ↓
Task 5 (new /cases route)
    ↓
Task 6 (old route redirect)
    ↓
Task 7 (copy citation button)
    ↓
Task 9 (update internal links)

Task 10 (CLAUDE.md) — independent, do anytime
```

Tasks 1→2 are sequential. After Task 2, Tasks 3 and 4 can run in parallel. After Task 4, Tasks 5→6→7→9 are sequential. Task 8 depends on Task 3. Task 10 is independent.
