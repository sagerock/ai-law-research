#!/usr/bin/env python3
"""
Con Law collection 15, Week 9 additions (2026-10-17), from Sage's Week 09 schedule
(dormant Commerce Clause, cont.; Art. IV Privileges & Immunities):

  All fifteen principal cases already exist in `cases`; they are appended to
  collection 15 in schedule order (09(A) -> 09(D)). National Pork Producers is
  cited by Peters as 143 S. Ct. 1142; the `cases` row carries 598 U.S. 356.

Collection notes are written separately (blank-only); see the law-school repo's
fall-2026/con-law/AGENTS.md. Idempotent.

Run from repo root:  python scripts/import_conlaw_week09_2026.py [--dry-run]
Requires PROD_DATABASE_URL (or DATABASE_URL inside the Railway Backend service).
"""

import asyncio
import os
import sys

import asyncpg

COLLECTION_ID = 15
# Schedule order, Week 09 Modules (A)-(D).
WEEK_09 = [
    "104847",    # Dean Milk Co. v. City of Madison, 340 U.S. 349
    "111715",    # Maine v. Taylor, 477 U.S. 131
    "109498",    # Hughes v. Alexandria Scrap Corp., 426 U.S. 794
    "110308",    # Reeves, Inc. v. Stake, 447 U.S. 429
    "110880",    # White v. Massachusetts Council of Constr. Employers, 460 U.S. 204
    "111189",    # South-Central Timber Dev. v. Wunnicke, 467 U.S. 82
    "108085",    # Pike v. Bruce Church, Inc., 397 U.S. 137
    "105890",    # Bibb v. Navajo Freight Lines, Inc., 359 U.S. 520
    "109771",    # Raymond Motor Transportation, Inc. v. Rice, 434 U.S. 429
    "110439",    # Kassel v. Consolidated Freightways Corp., 450 U.S. 662
    "10049695",  # National Pork Producers Council v. Ross, 598 U.S. 356
    "104563",    # Toomer v. Witsell, 334 U.S. 385
    "111097",    # United Bldg. & Constr. Trades Council v. Camden, 465 U.S. 208
    "109868",    # Baldwin v. Fish & Game Comm'n of Montana, 436 U.S. 371
    "111363",    # Supreme Court of New Hampshire v. Piper, 470 U.S. 274
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
            max_pos = await conn.fetchval(
                """SELECT COALESCE(MAX(pos), -1) FROM (
                       SELECT position AS pos FROM collection_cases WHERE collection_id = $1
                       UNION ALL
                       SELECT position AS pos FROM collection_legal_texts WHERE collection_id = $1
                   ) sub""",
                COLLECTION_ID,
            )
            for case_id in WEEK_09:
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
