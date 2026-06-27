#!/usr/bin/env python3
"""
Import the 17 Evidence exam-prep cases (Summer 2026 table-of-cases) into the
production Law Study Group database.

Source data comes from law-hub's already-verified cache (cases.db) — full
CourtListener opinions + citations fetched via the sub_opinions endpoint — so we
avoid re-fetching through the v4 citations format (which import_cited_missing's
fetch_case_from_api mishandles). Inserts use the same `cases` columns/SQL as the
canonical pipeline. court_id is left NULL; run fix_orphan_courts.py afterward to
backfill it from reporter_cite.

Run via:  railway run --service Backend -- <venv>/bin/python scripts/import_evidence_cases.py
"""

import asyncio
import json
import os
import re
import sqlite3
from datetime import datetime

import asyncpg

LAWHUB_DB = "/mnt/d/dev/law-hub/cases.db"
# Prefer the public proxy URL so this runs from a developer machine (the bare
# DATABASE_URL points at Railway's internal-only host).
DATABASE_URL = (
    os.getenv("DATABASE_PUBLIC_URL")
    or os.getenv("PROD_DATABASE_URL")
    or os.getenv("DATABASE_URL")
)

CLUSTER_IDS = [
    462454, 6486913, 8972075, 771786, 565200, 1180405, 2074658, 1207456,
    118074, 118367, 10014245, 4907763, 118337, 102164, 112049, 112257, 107359,
]


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def first_citation(citations_json):
    try:
        cites = json.loads(citations_json or "[]")
    except (json.JSONDecodeError, TypeError):
        return None
    for c in cites:
        if c.get("reporter"):
            return f"{c.get('volume','')} {c.get('reporter','')} {c.get('page','')}".strip()
    return None


def load_from_lawhub():
    db = sqlite3.connect(LAWHUB_DB)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT * FROM opinions WHERE cluster_id IN (%s)"
        % ",".join("?" * len(CLUSTER_IDS)),
        CLUSTER_IDS,
    ).fetchall()
    out = []
    for r in rows:
        content = r["plain_text"] or strip_html(r["html_with_citations"])
        decision_date = None
        if r["date_filed"]:
            try:
                decision_date = datetime.strptime(r["date_filed"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass
        out.append({
            "id": str(r["cluster_id"]),
            "title": r["case_name"],
            "decision_date": decision_date,
            "reporter_cite": first_citation(r["citations_json"]),
            "content": content or None,
            "source_url": r["absolute_url"] or None,
        })
    return out


async def main():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return

    cases = load_from_lawhub()
    print(f"Loaded {len(cases)} cases from law-hub cache")

    conn = await asyncpg.connect(DATABASE_URL)
    imported = skipped = failed = 0
    try:
        for c in cases:
            exists = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", c["id"])
            if exists:
                print(f"  skip (exists): {c['title']}")
                skipped += 1
                continue
            try:
                await conn.execute(
                    """
                    INSERT INTO cases (id, title, decision_date, court_id, reporter_cite,
                                       content, source_url, created_at)
                    VALUES ($1, $2, $3, NULL, $4, $5, $6, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        content = COALESCE(EXCLUDED.content, cases.content),
                        reporter_cite = COALESCE(EXCLUDED.reporter_cite, cases.reporter_cite),
                        updated_at = NOW()
                    """,
                    c["id"], c["title"], c["decision_date"], c["reporter_cite"],
                    c["content"], c["source_url"],
                )
                clen = len(c["content"] or "")
                print(f"  imported: {c['title']} | {c['reporter_cite']} | {clen:,} chars")
                imported += 1
            except Exception as e:
                print(f"  ERROR {c['title']}: {repr(e)[:120]}")
                failed += 1
    finally:
        await conn.close()

    print(f"\nImported: {imported}  Skipped: {skipped}  Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
