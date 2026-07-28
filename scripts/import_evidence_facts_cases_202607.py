#!/usr/bin/env python3
"""
Import the two Oregon dram-shop cases used in Evidence (Summer 2026) to
illustrate the adjudicative / legislative fact distinction.

The same fact — that people drive to and from taverns, so drunk driving is
foreseeable — is a *legislative* fact in Campbell (the court took notice of it
to justify adopting a common-law rule) and an *adjudicative* fact in Chartrand
(an element the jury had to find). Useful precisely because they pair.

Metadata only: content is left NULL so the row is a stub. Hydrate afterwards
through the backend's own endpoint, which runs the canonical assembler and
preserves typed opinion boundaries:

    curl -X POST https://backend-production-8940.up.railway.app/api/v1/cases/<id>/fetch-opinion

That endpoint is free and unauthenticated — the opinion is public record. Do not
fetch and insert opinion text here; a second assembly path is exactly what
`AI_COLLABORATION.md` warns against.

court_id is left NULL; run fix_orphan_courts.py afterwards to backfill it from
reporter_cite.

Run:  DATABASE_PUBLIC_URL=... .venv/bin/python scripts/import_evidence_facts_cases_202607.py
"""

import asyncio
import os
from datetime import date

import asyncpg

DATABASE_URL = (
    os.getenv("DATABASE_PUBLIC_URL")
    or os.getenv("PROD_DATABASE_URL")
    or os.getenv("DATABASE_URL")
)

CASES = [
    {
        "id": "1177100",
        "title": "Chartrand v. Coos Bay Tavern, Inc.",
        "decision_date": date(1985, 2, 20),
        "reporter_cite": "298 Or. 689",
        "source_url": "https://www.courtlistener.com/opinion/1177100/chartrand-v-coos-bay-tavern-inc/",
    },
    {
        # Note: the class slide dates this 1979. CourtListener and the A.L.R.
        # annotation (97 A.L.R.3d 522) both put it at 1977.
        "id": "1186251",
        "title": "Campbell v. Carpenter",
        "decision_date": date(1977, 7, 20),
        "reporter_cite": "279 Or. 237",
        "source_url": "https://www.courtlistener.com/opinion/1186251/campbell-v-carpenter/",
    },
]


async def main():
    if not DATABASE_URL:
        raise SystemExit("Set DATABASE_PUBLIC_URL (or PROD_DATABASE_URL / DATABASE_URL).")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for c in CASES:
            existing = await conn.fetchrow(
                "SELECT id, length(content) AS n FROM cases WHERE id = $1", c["id"]
            )
            if existing and (existing["n"] or 0) > 200:
                print(f"  = {c['title']} already present with {existing['n']:,} chars — skipped")
                continue

            await conn.execute(
                """
                INSERT INTO cases (id, title, decision_date, court_id, reporter_cite,
                                   content, source_url, created_at)
                VALUES ($1, $2, $3, NULL, $4, NULL, $5, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    decision_date = COALESCE(EXCLUDED.decision_date, cases.decision_date),
                    reporter_cite = COALESCE(EXCLUDED.reporter_cite, cases.reporter_cite),
                    source_url = COALESCE(EXCLUDED.source_url, cases.source_url),
                    updated_at = NOW()
                """,
                c["id"], c["title"], c["decision_date"], c["reporter_cite"], c["source_url"],
            )
            print(f"  + {c['title']} | {c['reporter_cite']} | stub inserted ({c['id']})")
    finally:
        await conn.close()

    print("\nNow hydrate each via POST /api/v1/cases/<id>/fetch-opinion, then "
          "run fix_orphan_courts.py to backfill court_id.")


if __name__ == "__main__":
    asyncio.run(main())
