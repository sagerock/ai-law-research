# Citation-Native URLs Design

**Date:** 2026-03-28
**Status:** Approved
**Goal:** Replace opaque `/case/{id}` URLs with citation-native `/cases/{citation-slug}` URLs, positioning lawstudygroup.com as the open citation layer for American case law.

## URL Schema

### Canonical format: `/cases/{volume}-{reporter}-{page}`

| Reporter Cite | URL |
|---|---|
| `550 U.S. 544` | `/cases/550-us-544` |
| `103 F.3d 144` | `/cases/103-f3d-144` |
| `51 Cal. 2d 409` | `/cases/51-cal-2d-409` |
| `121 U.S. App. D.C. 315` | `/cases/121-us-app-dc-315` |
| `206 F. App'x 317` | `/cases/206-f-appx-317` |

### Fallback for cases without reporter cite: `/cases/{name-slug}`

| Case Title | URL |
|---|---|
| `Wood v. Lucy, Lady Duff-Gordon` | `/cases/wood-v-lucy-lady-duff-gordon` |

### Resolution priority

1. Parse slug as citation pattern (`{number}-{reporter}-{number}`) → query by normalized reporter cite
2. Treat slug as case name slug → query by slugified title
3. Ambiguous → disambiguation page (future, not in v1 — return first match for now)
4. Not found → 404

## Reporter Normalization

A standalone, testable module at `backend/citation_utils.py` with its own test file `backend/test_citation_utils.py`.

### Bidirectional mapping

**Slug to DB format** (URL → database query):

| Slug | DB Value |
|---|---|
| `us` | `U.S.` |
| `f2d` | `F.2d` |
| `f3d` | `F.3d` |
| `f-supp` | `F. Supp.` |
| `f-supp-2d` | `F. Supp. 2d` |
| `f-appx` | `F. App'x` |
| `ne` | `N.E.` |
| `ne2d` | `N.E.2d` |
| `nw` | `N.W.` |
| `nw2d` | `N.W.2d` |
| `cal-2d` | `Cal. 2d` |
| `p2d` | `P.2d` |
| `p3d` | `P.3d` |
| `us-app-dc` | `U.S. App. D.C.` |
| `s-ct` | `S. Ct.` |
| `so-2d` | `So. 2d` |
| `sw2d` | `S.W.2d` |
| `a` | `A.` |
| `a2d` | `A.2d` |
| `ad2d` | `A.D.2d` |
| `ny` | `N.Y.` |
| `ny2d` | `N.Y.2d` |
| `va` | `Va.` |
| `mass` | `Mass.` |
| `neb` | `Neb.` |
| `minn` | `Minn.` |
| `ohio-op` | `Ohio Op.` |
| `ohio-law-abs` | `Ohio Law. Abs.` |

Plus a **generic algorithm** for reporters not in the table: strip periods/apostrophes, lowercase, collapse whitespace to hyphens.

The reverse mapping (DB → slug) is derived from the same table.

### Normalization rules

1. Strip periods and apostrophes
2. Lowercase everything
3. Collapse spaces to hyphens
4. Explicit lookup table overrides generic algorithm for known reporters

### TypeScript equivalent

A mirrored normalization module at `frontend/lib/citationUrls.ts` for generating canonical URLs client-side (e.g., for the "Cite this case" button and internal links).

## Backend: Resolver Endpoint

### `GET /api/v1/cases/resolve/{slug}`

**Input:** URL slug (e.g., `550-us-544` or `wood-v-lucy-lady-duff-gordon`)

**Output:**
```json
{
  "case_id": "145730",
  "canonical_slug": "550-us-544"
}
```

**Logic:**
1. If slug is a pure numeric string → treat as legacy case ID → `SELECT id, reporter_cite, title FROM cases WHERE id = $1`
2. Try parsing slug as citation: extract leading volume number, trailing page number, middle reporter slug
3. If citation pattern → denormalize reporter → `SELECT id, reporter_cite, title FROM cases WHERE reporter_cite = $1`
4. If no citation match → treat as name slug → `SELECT id, reporter_cite, title FROM cases WHERE LOWER(REGEXP_REPLACE(title, '[^a-z0-9]+', '-', 'gi')) = $1`
5. Not found → 404

**Note:** The name slug query uses `REGEXP_REPLACE` at query time. At ~27k cases this is fast enough. If the table grows significantly, consider adding a materialized `title_slug` column.

**Caching:** `Cache-Control: public, max-age=86400` (citations are immutable).

**Location:** Added to `backend/main.py` using functions from `backend/citation_utils.py`.

## Frontend: New Route

### `frontend/app/cases/[...slug]/page.tsx`

Next.js catch-all route handling all citation URLs.

**Server-side flow:**
1. Join slug segments: `["550-us-544"]` → `"550-us-544"`
2. Call `GET /api/v1/cases/resolve/{slug}` → get `case_id` and `canonical_slug`
3. If URL slug !== `canonical_slug` → **redirect** to canonical URL
4. Fetch case data via existing `GET /api/v1/cases/{case_id}`
5. Render with existing `CaseDetailClient` component

### `generateMetadata()`

- Title: `Bell Atlantic Corp. v. Twombly | Sage's Study Group`
- Canonical: `<link rel="canonical" href="https://lawstudygroup.com/cases/550-us-544" />`
- Open Graph description includes citation

### Old `/case/[id]` route modification

- Calls resolve endpoint with the numeric ID
- Gets back canonical slug
- **301 redirects** to `/cases/{canonical_slug}`
- Preserves all existing link equity

## "Cite This Case" Button

Added to `CaseDetailClient` component. Copies to clipboard:

```
Bell Atlantic Corp. v. Twombly, 550 U.S. 544 (2007)
https://lawstudygroup.com/cases/550-us-544
```

Format: `{title}, {reporter_cite} ({year})\n{canonical_url}`

For cases without reporter cite:
```
Wood v. Lucy, Lady Duff-Gordon (1918)
https://lawstudygroup.com/cases/wood-v-lucy-lady-duff-gordon
```

## Sitemap Update

Update `frontend/app/sitemap.ts` to emit `/cases/{slug}` URLs instead of `/case/{id}`. The backend sitemap endpoint (`GET /api/v1/sitemap/cases`) will return `canonical_slug` alongside case IDs so the frontend can build the right URLs.

## Files Changed

| File | Change |
|---|---|
| `backend/citation_utils.py` | **New** — reporter normalization, slug parsing, slug generation |
| `backend/test_citation_utils.py` | **New** — test suite for citation_utils |
| `backend/main.py` | Add `GET /api/v1/cases/resolve/{slug}`, update sitemap endpoint |
| `frontend/lib/citationUrls.ts` | **New** — TypeScript reporter normalization + URL generation |
| `frontend/app/cases/[...slug]/page.tsx` | **New** — citation URL route with SSR |
| `frontend/app/case/[id]/page.tsx` | **Modified** — 301 redirect to canonical citation URL |
| `frontend/app/case/[id]/CaseDetailClient.tsx` | **Modified** — add "Cite this case" button |
| `frontend/app/sitemap.ts` | **Modified** — use citation slugs |

## Out of Scope (v1)

- Disambiguation pages for ambiguous name slugs (return first match for now)
- Short-name aliases for landmark cases (e.g., `/cases/twombly`)
- Public API for external tools to resolve citations
- Year + name format URLs (e.g., `/cases/2007/twombly`)
