#!/usr/bin/env python3
"""
One-off cleanup for the Cosby evidence case (id 10315392):
  - title:  "Com. v. Cosby Jr., W."  ->  "Commonwealth v. Cosby"
  - court:  NULL  ->  "Superior Court of Pennsylvania" (get-or-create in courts)

The generic fix_orphan_courts.py maps "A.3d" only to a vague "State Court";
Cosby is specifically the Pa. Superior Court (224 A.3d 372, 2019), so set it exactly.

Run from repo root:  python scripts/fix_cosby_202607.py
Requires PROD_DATABASE_URL in .env / environment.
"""

import asyncio
import os

import asyncpg

CASE_ID = "10315392"
NEW_TITLE = "Commonwealth v. Cosby"
COURT_NAME = "Superior Court of Pennsylvania"
COURT_JURISDICTION = "state"
COURT_LEVEL = "appellate"


def load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


async def main():
    load_env()
    db_url = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: PROD_DATABASE_URL not set")
        return

    conn = await asyncpg.connect(db_url)
    try:
        before = await conn.fetchrow(
            "SELECT title, court_id, reporter_cite FROM cases WHERE id = $1", CASE_ID
        )
        if not before:
            print(f"ERROR: case {CASE_ID} not found")
            return
        print(f"before: title={before['title']!r} court_id={before['court_id']} "
              f"cite={before['reporter_cite']!r}")

        # get-or-create the court row
        court_id = await conn.fetchval("SELECT id FROM courts WHERE name = $1", COURT_NAME)
        if court_id is None:
            court_id = await conn.fetchval(
                """INSERT INTO courts (name, jurisdiction, level)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                   RETURNING id""",
                COURT_NAME, COURT_JURISDICTION, COURT_LEVEL,
            )
            print(f"created court {COURT_NAME!r} -> id {court_id}")
        else:
            print(f"court {COURT_NAME!r} exists -> id {court_id}")

        await conn.execute(
            "UPDATE cases SET title = $1, court_id = $2, updated_at = NOW() WHERE id = $3",
            NEW_TITLE, court_id, CASE_ID,
        )

        after = await conn.fetchrow(
            """SELECT c.title, ct.name AS court_name, c.reporter_cite
               FROM cases c LEFT JOIN courts ct ON c.court_id = ct.id
               WHERE c.id = $1""",
            CASE_ID,
        )
        print(f"after:  title={after['title']!r} court={after['court_name']!r} "
              f"cite={after['reporter_cite']!r}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
