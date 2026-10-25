#!/usr/bin/env python3
"""
Con Law collection 15, Week 10 additions (2026-10-25), from Sage's Week 10 schedule
(separation of powers: Youngstown, nondelegation, major questions), plus a private
per-week collection "Con Law – Week 10" holding the same cases (like Week 9's #21).

  - West Virginia v. EPA, 597 U.S. 697 (2022)          [cluster 6623244, revised slip op]
  - Learning Resources, Inc. v. Trump (Feb. 20, 2026)  [cluster 10799354, 2/23/26 revision]
    Neither is in `cases`. Imported as stubs; POST /api/v1/cases/<id>/fetch-opinion
    hydrates them from CourtListener. Learning Resources' cite (607 U.S. 229) is
    Peters's; CourtListener has no reporter cite yet. Row 10595582 is the D.D.C. case.
  - Gundy v. United States (4631442) exists as a citer stub with no cite; its cite is
    filled in here and fetch-opinion hydrates it.
  - Youngstown (105018) carried a parallel cite (62 Ohio Law. Abs. 417); set to 343 U.S. 579.
  - Panama Refining and Biden v. Nebraska exist; Schechter is already in collection 15.

Idempotent. Run from repo root:  python scripts/import_conlaw_week10_2026.py [--dry-run]
Requires PROD_DATABASE_URL (or DATABASE_URL inside the Railway Backend service).
"""

import asyncio
import json
import os
import sys
from datetime import date

import asyncpg

COLLECTION_ID = 15
WEEK_COLLECTION = {
    "name": "Con Law – Week 10",
    "description": (
        "Week 10 (Oct 19-25) principal cases: separation of powers — Youngstown and "
        "sources of executive power, nondelegation, and the major questions doctrine. "
        "Also in the main Con Law collection."
    ),
    "subject": "Con Law",
}
STUBS = [
    {
        "id": "6623244",
        "title": "West Virginia v. EPA",
        "docket_number": "No. 20-1530",
        "decision_date": date(2022, 6, 30),
        "reporter_cite": "597 U.S. 697",
        "source_url": "https://www.courtlistener.com/opinion/6623244/west-virginia-v-epa/",
        "metadata": {
            "source": "courtlistener_api",
            "subject": "constitutional-law",
            "precedential_status": "Published",
            "courtlistener_docket_id": 63588171,
            "courtlistener_cluster_id": 6623244,
            "stub": True,
        },
    },
    {
        "id": "10799354",
        "title": "Learning Resources, Inc. v. Trump",
        "docket_number": "No. 24-1287",
        "decision_date": date(2026, 2, 20),
        "reporter_cite": "607 U.S. 229",
        "source_url": "https://www.courtlistener.com/opinion/10799354/learning-resources-inc-v-trump/",
        "metadata": {
            "source": "courtlistener_api",
            "subject": "constitutional-law",
            "precedential_status": "Published",
            "courtlistener_docket_id": 71877961,
            "courtlistener_cluster_id": 10799354,
            "stub": True,
        },
    },
]
CITE_FIXES = {
    "4631442": ("588 U.S. 128", "No. 17-6086"),  # Gundy v. United States
    "105018": ("343 U.S. 579", None),            # Youngstown Sheet & Tube Co. v. Sawyer
}
# Schedule order, Week 10 Modules (B)-(D).
WEEK_10 = [
    "105018",    # Youngstown Sheet & Tube Co. v. Sawyer, 343 U.S. 579
    "102474",    # A.L.A. Schechter Poultry Corp. v. United States, 295 U.S. 495
    "102353",    # Panama Refining Co. v. Ryan, 293 U.S. 388
    "4631442",   # Gundy v. United States, 588 U.S. 128
    "6623244",   # West Virginia v. EPA, 597 U.S. 697
    "10049655",  # Biden v. Nebraska, 600 U.S. 477
    "10799354",  # Learning Resources, Inc. v. Trump, 607 U.S. 229
]


def load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip('"'))


async def append(conn, collection_id, case_ids):
    max_pos = await conn.fetchval(
        """SELECT COALESCE(MAX(pos), -1) FROM (
               SELECT position AS pos FROM collection_cases WHERE collection_id = $1
               UNION ALL
               SELECT position AS pos FROM collection_legal_texts WHERE collection_id = $1
           ) sub""",
        collection_id,
    )
    for case_id in case_ids:
        if not await conn.fetchval("SELECT 1 FROM cases WHERE id = $1", case_id):
            raise RuntimeError(f"missing from cases: {case_id}; rolling back")
        if await conn.fetchval(
            "SELECT 1 FROM collection_cases WHERE collection_id = $1 AND case_id = $2",
            collection_id, case_id,
        ):
            print(f"skip (in collection {collection_id}): {case_id}")
            continue
        max_pos += 1
        await conn.execute(
            "INSERT INTO collection_cases (collection_id, case_id, position) VALUES ($1, $2, $3)",
            collection_id, case_id, max_pos,
        )
        print(f"collection {collection_id}: added {case_id} at position {max_pos}")


async def main(dry_run: bool):
    load_env()
    db_url = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        sys.exit("ERROR: PROD_DATABASE_URL not set")

    conn = await asyncpg.connect(db_url)
    try:
        async with conn.transaction():
            for m in STUBS:
                if await conn.fetchval("SELECT 1 FROM cases WHERE id = $1", m["id"]):
                    print(f"skip (exists): {m['title']} ({m['id']})")
                    continue
                await conn.execute(
                    """INSERT INTO cases (id, title, court_id, docket_number, decision_date,
                                          reporter_cite, precedential, source_url, metadata,
                                          created_at, updated_at)
                       VALUES ($1, $2, 13, $3, $4, $5, TRUE, $6, $7, NOW(), NOW())""",
                    m["id"], m["title"], m["docket_number"], m["decision_date"],
                    m["reporter_cite"], m["source_url"], json.dumps(m["metadata"]),
                )
                print(f"imported stub: {m['title']} ({m['id']})")

            for case_id, (cite, docket) in CITE_FIXES.items():
                await conn.execute(
                    """UPDATE cases SET reporter_cite = $2, court_id = COALESCE(court_id, 13),
                              docket_number = COALESCE(docket_number, $3), updated_at = NOW()
                        WHERE id = $1 AND reporter_cite IS DISTINCT FROM $2""",
                    case_id, cite, docket,
                )

            await append(conn, COLLECTION_ID, WEEK_10)

            owner = await conn.fetchval("SELECT user_id FROM collections WHERE id = $1", COLLECTION_ID)
            week_id = await conn.fetchval(
                "SELECT id FROM collections WHERE user_id = $1 AND name = $2",
                owner, WEEK_COLLECTION["name"],
            )
            if week_id is None:
                week_id = await conn.fetchval(
                    """INSERT INTO collections (user_id, name, description, is_public, subject,
                                                created_at, updated_at)
                       VALUES ($1, $2, $3, FALSE, $4, NOW(), NOW()) RETURNING id""",
                    owner, WEEK_COLLECTION["name"], WEEK_COLLECTION["description"],
                    WEEK_COLLECTION["subject"],
                )
                print(f"created collection {week_id}: {WEEK_COLLECTION['name']}")
            await append(conn, week_id, WEEK_10)

            if dry_run:
                raise RuntimeError("dry run: rolling back")
    except RuntimeError as e:
        print(e)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
