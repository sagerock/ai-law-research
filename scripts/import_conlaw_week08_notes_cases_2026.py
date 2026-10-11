#!/usr/bin/env python3
"""
Con Law collection 15, Week 8 casebook-notes cases (2026-10-11). Sage's Week 8 outline
covers five notes cases that were not yet in the collection:

  - Riegel v. Medtronic, Inc., 552 U.S. 312 (2008)                      [145831]  08(A)
  - Chamber of Commerce v. Whiting, 563 U.S. 582 (2011)                 [217515]  08(A)
  - Hines v. Davidowitz, 312 U.S. 52 (1941)                             [103438]  08(B)
  - C & A Carbone, Inc. v. Town of Clarkstown, 511 U.S. 383 (1994)      [1087961] 08(D)
  - United Haulers Ass'n v. Oneida-Herkimer, 550 U.S. 330 (2007)        [145739]  08(D)

All five already exist in `cases`. Hines's row had no reporter cite or court; both are
filled from CourtListener cluster 103438 (312 U.S. 52, docket in `scotus`), only where
NULL. Cases are appended in module order with the course note the law-school repo's
build_collection_note() produces from case_metadata.json (passed in as NOTES, blank-only).
Idempotent.

Production has no public Postgres proxy, so run it inside the backend container:
    python3 scripts/import_conlaw_week08_notes_cases_2026.py --bundle notes.json \
        | railway ssh -s Backend -- env DRY_RUN=1 python -
"""

import asyncio
import json
import os
import sys

COLLECTION_ID = 15
SUPREME_COURT_ID = 13
CASES = ["145831", "217515", "103438", "1087961", "145739"]
HINES = {"id": "103438", "reporter_cite": "312 U.S. 52"}
NOTES: dict[str, str] = {}


async def main(database_url: str, dry_run: bool):
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        transaction = conn.transaction()
        await transaction.start()
        try:
            status = await conn.execute(
                """UPDATE cases SET reporter_cite = COALESCE(reporter_cite, $2),
                                    court_id = COALESCE(court_id, $3), updated_at = NOW()
                   WHERE id = $1 AND (reporter_cite IS NULL OR court_id IS NULL)""",
                HINES["id"], HINES["reporter_cite"], SUPREME_COURT_ID,
            )
            print(f"Hines metadata: {status}")

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
                    raise RuntimeError(f"missing from cases: {case_id}")
                note = NOTES.get(case_id)
                if await conn.fetchval(
                    "SELECT 1 FROM collection_cases WHERE collection_id = $1 AND case_id = $2",
                    COLLECTION_ID, case_id,
                ):
                    await conn.execute(
                        """UPDATE collection_cases SET notes = $3
                           WHERE collection_id = $1 AND case_id = $2
                             AND (notes IS NULL OR btrim(notes) = '')""",
                        COLLECTION_ID, case_id, note,
                    )
                    print(f"skip (in collection): {case_id}")
                    continue
                max_pos += 1
                await conn.execute(
                    """INSERT INTO collection_cases (collection_id, case_id, position, notes)
                       VALUES ($1, $2, $3, $4)""",
                    COLLECTION_ID, case_id, max_pos, note,
                )
                print(f"added {case_id} at position {max_pos}")
        except BaseException:
            await transaction.rollback()
            raise
        if dry_run:
            await transaction.rollback()
            print("dry run: rolled back")
        else:
            await transaction.commit()
            print("committed")
    finally:
        await conn.close()


if __name__ == "__main__" and sys.argv[0] != "-":
    if "--bundle" not in sys.argv:
        sys.exit("usage: --bundle <notes.json> | railway ssh -s Backend -- env DRY_RUN=0 python -")
    notes = json.loads(open(sys.argv[sys.argv.index("--bundle") + 1]).read())
    missing = [c for c in CASES if not notes.get(c)]
    if missing:
        sys.exit(f"notes missing for {missing}")
    sys.stdout.write(
        open(__file__).read()
        + f"\nNOTES = json.loads({json.dumps(json.dumps(notes))})"
        + "\nasyncio.run(main(os.environ['DATABASE_URL'], os.environ.get('DRY_RUN', '1') != '0'))\n"
    )
