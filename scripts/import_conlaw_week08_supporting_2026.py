#!/usr/bin/env python3
"""
Con Law collection 15, Week 8 supporting cases (2026-10-11). Casebook notes cases (pp. 382-83)
that Peters taught in Lecture 08(B) and tested in Quiz 08(B):

  - Wyeth v. Levine, 555 U.S. 555 (2009)                        [145902]
  - PLIVA, Inc. v. Mensing, 564 U.S. 604 (2011)                 [219510]
  - Mutual Pharmaceutical Co. v. Bartlett, 570 U.S. 472 (2013)  [9068915]

All three already exist in `cases`; this only appends them to collection 15. Idempotent.

Run from repo root:  python scripts/import_conlaw_week08_supporting_2026.py [--dry-run]
Requires PROD_DATABASE_URL (or DATABASE_URL inside the Railway Backend service).
"""

import asyncio
import os
import sys

import asyncpg

COLLECTION_ID = 15
CASES = ["145902", "219510", "9068915"]


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
            max_pos = await conn.fetchval(
                """SELECT COALESCE(MAX(pos), -1) FROM (
                       SELECT position AS pos FROM collection_cases WHERE collection_id = $1
                       UNION ALL
                       SELECT position AS pos FROM collection_legal_texts WHERE collection_id = $1
                   ) sub""",
                COLLECTION_ID,
            )
            for case_id in CASES:
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
