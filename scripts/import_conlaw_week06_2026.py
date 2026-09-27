#!/usr/bin/env python3
"""
Con Law collection 15, Week 6 repairs (2026-09-27), from Sage's Week 06 schedule:

  - Pennhurst State School & Hospital v. Halderman, 451 U.S. 1 (1981)  [cluster 110458]
    The assigned spending-clause case was missing from `cases`; collection 15 held the
    1984 Eleventh Amendment decision (111094, 465 U.S. 89) in its place. The 1981 case
    is imported as a stub (hydrated via POST /api/v1/cases/110458/fetch-opinion) and
    swapped into 111094's collection slot, keeping position 69. 111094 stays in `cases`.
  - Module 06(G) Tenth Amendment cases appended to collection 15: Garcia (111308),
    New York v. United States (112768), Printz (118148), Reno v. Condon (118327),
    Murphy v. NCAA (4497655). All already existed in `cases` with S3 opinion text.

Collection notes were written separately (blank-only) from the law-school repo's
fall-2026/con-law/materials/tortwell-qdrant/case_metadata.json. This script only records
and can re-apply the membership changes. Idempotent.

Run from repo root:  python scripts/import_conlaw_week06_2026.py [--dry-run]
Requires PROD_DATABASE_URL in .env / environment.
"""

import asyncio
import json
import os
import sys
from datetime import date

import asyncpg

COLLECTION_ID = 15
PENNHURST_1981 = {
    "id": "110458",
    "title": "Pennhurst State School and Hospital v. Halderman",
    "court_id": 13,  # Supreme Court of the United States
    "docket_number": "No. 79-1404",
    "decision_date": date(1981, 4, 20),
    "reporter_cite": "451 U.S. 1",
    "source_url": "https://www.courtlistener.com/opinion/110458/",
    "metadata": {
        "source": "courtlistener_api",
        "subject": "constitutional-law",
        "precedential_status": "Published",
        "courtlistener_cluster_id": 110458,
        "courtlistener_docket_id": 588048,
        "stub": True,
        "class_material": "Con Law Week 06 schedule, Module 06(B)",
    },
}
PENNHURST_1984 = "111094"
MODULE_06G = ["111308", "112768", "118148", "118327", "4497655"]


def load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip('"'))


async def main(dry_run: bool):
    load_env()
    db_url = os.getenv("PROD_DATABASE_URL")
    if not db_url:
        sys.exit("ERROR: PROD_DATABASE_URL not set")

    conn = await asyncpg.connect(db_url)
    try:
        async with conn.transaction():
            p = PENNHURST_1981
            if await conn.fetchval("SELECT 1 FROM cases WHERE id = $1", p["id"]):
                print(f"skip (exists): {p['title']} ({p['id']})")
            else:
                await conn.execute(
                    """INSERT INTO cases (id, title, court_id, docket_number, decision_date,
                                          reporter_cite, precedential, source_url, metadata,
                                          created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7, $8, NOW(), NOW())""",
                    p["id"], p["title"], p["court_id"], p["docket_number"],
                    p["decision_date"], p["reporter_cite"], p["source_url"],
                    json.dumps(p["metadata"]),
                )
                print(f"imported stub: {p['title']} ({p['id']})")

            status = await conn.execute(
                """UPDATE collection_cases SET case_id = $2
                   WHERE collection_id = $1 AND case_id = $3
                     AND NOT EXISTS (SELECT 1 FROM collection_cases
                                     WHERE collection_id = $1 AND case_id = $2)""",
                COLLECTION_ID, p["id"], PENNHURST_1984,
            )
            print(f"swap {PENNHURST_1984} -> {p['id']}: {status}")

            max_pos = await conn.fetchval(
                """SELECT COALESCE(MAX(pos), -1) FROM (
                       SELECT position AS pos FROM collection_cases WHERE collection_id = $1
                       UNION ALL
                       SELECT position AS pos FROM collection_legal_texts WHERE collection_id = $1
                   ) sub""",
                COLLECTION_ID,
            )
            for case_id in MODULE_06G:
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
