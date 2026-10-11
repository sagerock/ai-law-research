#!/usr/bin/env python3
"""
Con Law collection 15, Week 8 additions (2026-10-11), from Sage's Week 08 schedule
(preemption; dormant Commerce Clause):

  - Monsanto Co. v. Durnell, No. 24-1068 (June 25, 2026)   [cluster 10880244]
    Not in `cases`. Imported as a stub; POST /api/v1/cases/10880244/fetch-opinion then
    hydrates it from CourtListener (same path as Callais). The S. Ct. cite comes from
    Peters's edited Brightspace copy; CourtListener has no reporter cite yet.
  - The other eleven principal cases already exist in `cases` and are appended to
    collection 15 in schedule order (08(A) -> 08(D)). Cooley's row carries no reporter
    cite; Exxon's decision_date (1978-10-02) is CourtListener's, the cite is correct.

Collection notes are written separately (blank-only) by the law-school repo's
fall-2026/con-law/materials/tortwell-qdrant/sync_collection.py --fill-notes.
Idempotent.

Run from repo root:  python scripts/import_conlaw_week08_2026.py [--dry-run]
Requires PROD_DATABASE_URL (or DATABASE_URL inside the Railway Backend service).
"""

import asyncio
import json
import os
import sys
from datetime import date

import asyncpg

COLLECTION_ID = 15
MONSANTO = {
    "id": "10880244",
    "title": "Monsanto Co. v. Durnell",
    "court_id": 13,  # Supreme Court of the United States
    "docket_number": "No. 24-1068",
    "decision_date": date(2026, 6, 25),
    "reporter_cite": "146 S. Ct. 2001",
    "source_url": "https://www.courtlistener.com/opinion/10880244/monsanto-v-durnell/",
    "metadata": {
        "source": "courtlistener_api",
        "subject": "constitutional-law",
        "class_material": "Monsanto Company v Durnell-edited 09.26.docx",
        "precedential_status": "Published",
        "courtlistener_docket_id": 72483540,
        "courtlistener_cluster_id": 10880244,
        "stub": True,
    },
}
# Schedule order, Week 08 Modules (A)-(D).
WEEK_08 = [
    "118458",    # Lorillard Tobacco Co. v. Reilly, 533 U.S. 525
    "10880244",  # Monsanto Co. v. Durnell (2026)
    "106601",    # Florida Lime & Avocado Growers v. Paul, 373 U.S. 132
    "110919",    # Pacific Gas & Electric v. State Energy Comm'n, 461 U.S. 190
    "803270",    # Arizona v. United States, 567 U.S. 387
    "4632952",   # Tennessee Wine & Spirits Retailers Ass'n v. Thomas, 139 S. Ct. 2449
    "86696",     # Cooley v. Board of Wardens, 53 U.S. (12 How.) 299
    "109916",    # City of Philadelphia v. New Jersey, 437 U.S. 617
    "117855",    # West Lynn Creamery v. Healy, 512 U.S. 186
    "109703",    # Hunt v. Washington State Apple Advertising Comm'n, 432 U.S. 333
    "109896",    # Exxon Corp. v. Governor of Maryland, 437 U.S. 117
    "110380",    # Minnesota v. Clover Leaf Creamery Co., 449 U.S. 456
]


def load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip('"'))


async def main(dry_run: bool):
    load_env()
    db_url = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        sys.exit("ERROR: PROD_DATABASE_URL not set")

    conn = await asyncpg.connect(db_url)
    try:
        async with conn.transaction():
            m = MONSANTO
            if await conn.fetchval("SELECT 1 FROM cases WHERE id = $1", m["id"]):
                print(f"skip (exists): {m['title']} ({m['id']})")
            else:
                await conn.execute(
                    """INSERT INTO cases (id, title, court_id, docket_number, decision_date,
                                          reporter_cite, precedential, source_url, metadata,
                                          created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7, $8, NOW(), NOW())""",
                    m["id"], m["title"], m["court_id"], m["docket_number"],
                    m["decision_date"], m["reporter_cite"], m["source_url"],
                    json.dumps(m["metadata"]),
                )
                print(f"imported stub: {m['title']} ({m['id']})")

            max_pos = await conn.fetchval(
                """SELECT COALESCE(MAX(pos), -1) FROM (
                       SELECT position AS pos FROM collection_cases WHERE collection_id = $1
                       UNION ALL
                       SELECT position AS pos FROM collection_legal_texts WHERE collection_id = $1
                   ) sub""",
                COLLECTION_ID,
            )
            for case_id in WEEK_08:
                if not await conn.fetchval("SELECT 1 FROM cases WHERE id = $1", case_id):
                    raise RuntimeError(f"missing from cases: {case_id}; rolling back")
                if await conn.fetchval(
                    "SELECT 1 FROM collection_cases WHERE collection_id = $1 AND case_id = $2",
                    COLLECTION_ID, case_id,
                ):
                    print(f"skip (in collection): {case_id}")
                    continue
                max_pos += 1
                await conn.execute(
                    "INSERT INTO collection_cases (collection_id, case_id, position) VALUES ($1, $2, $3)",
                    COLLECTION_ID, case_id, max_pos,
                )
                print(f"added {case_id} at position {max_pos}")

            if dry_run:
                raise RuntimeError("dry run: rolling back")
    except RuntimeError as e:
        print(e)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
