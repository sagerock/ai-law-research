#!/usr/bin/env python3

"""Add cases from test_brief.txt to the database"""

import asyncio
import asyncpg
from datetime import datetime
import uuid

async def add_cases():
    conn = await asyncpg.connect('postgresql://legal_user:legal_pass@localhost:5432/legal_research')

    # Cases from test_brief.txt
    cases = [
        {
            "case_name": "International Shoe Co. v. Washington",
            "court_id": "scotus",
            "citation": "326 U.S. 310",
            "year": 1945,
            "content": "Landmark case establishing minimum contacts standard for personal jurisdiction."
        },
        {
            "case_name": "World-Wide Volkswagen Corp. v. Woodson",
            "court_id": "scotus",
            "citation": "444 U.S. 286",
            "year": 1980,
            "content": "Supreme Court case on personal jurisdiction and purposeful availment."
        },
        {
            "case_name": "Ford Motor Co. v. Montana Eighth Judicial District Court",
            "court_id": "scotus",
            "citation": "141 S. Ct. 1017",
            "year": 2021,
            "content": "Recent Supreme Court case on specific jurisdiction."
        },
        {
            "case_name": "Celotex Corp. v. Catrett",
            "court_id": "scotus",
            "citation": "477 U.S. 317",
            "year": 1986,
            "content": "Summary judgment standard - moving party burden."
        },
        {
            "case_name": "Anderson v. Liberty Lobby, Inc.",
            "court_id": "scotus",
            "citation": "477 U.S. 242",
            "year": 1986,
            "content": "Summary judgment - genuine issue of material fact."
        },
        {
            "case_name": "Matsushita Electric Industrial Co. v. Zenith Radio Corp.",
            "court_id": "scotus",
            "citation": "475 U.S. 574",
            "year": 1986,
            "content": "Summary judgment trilogy case."
        },
        {
            "case_name": "Scott v. Harris",
            "court_id": "scotus",
            "citation": "550 U.S. 372",
            "year": 2007,
            "content": "Summary judgment - view evidence in light most favorable to nonmoving party."
        },
        {
            "case_name": "Mathews v. Eldridge",
            "court_id": "scotus",
            "citation": "424 U.S. 319",
            "year": 1976,
            "content": "Due process balancing test."
        },
        {
            "case_name": "Goldberg v. Kelly",
            "court_id": "scotus",
            "citation": "397 U.S. 254",
            "year": 1970,
            "content": "Due process - notice and opportunity to be heard."
        }
    ]

    added = 0
    for case in cases:
        case_id = str(uuid.uuid4())

        # Check if case already exists
        existing = await conn.fetchval(
            "SELECT id FROM cases WHERE case_name = $1",
            case['case_name']
        )

        if existing:
            print(f"Already exists: {case['case_name']}")
            continue

        # Insert the case
        await conn.execute("""
            INSERT INTO cases (id, case_name, court_id, date_filed, content, metadata, citation_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
            case_id,
            case['case_name'],
            case['court_id'],
            datetime(case['year'], 1, 1),
            case['content'],
            f'{{"citation": "{case["citation"]}", "year": {case["year"]}}}',
            10  # Give them some citation count
        )

        print(f"✅ Added: {case['case_name']} ({case['citation']})")
        added += 1

    await conn.close()
    print(f"\n✨ Added {added} cases from test_brief.txt!")

if __name__ == "__main__":
    asyncio.run(add_cases())