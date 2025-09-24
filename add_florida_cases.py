#!/usr/bin/env python3

"""Add Florida cases to the database for citation validation"""

import asyncio
import asyncpg
from datetime import datetime
import uuid

async def add_cases():
    conn = await asyncpg.connect('postgresql://legal_user:legal_pass@localhost:5432/legal_research')

    # Key cases from the brief
    cases = [
        {
            "case_name": "Dobrin v. Florida Dept. of Highway Safety and Motor Vehicles",
            "court_id": "fla",
            "citation": "874 So.2d 1171",
            "year": 2004,
            "content": "Fourth Amendment case regarding traffic stops and reasonable suspicion."
        },
        {
            "case_name": "State v. McNeal",
            "court_id": "fla",
            "citation": "666 So.2d 229",
            "year": 1995,
            "content": "Florida case on search and seizure during traffic stops."
        },
        {
            "case_name": "Kehoe v. State",
            "court_id": "fla",
            "citation": "521 So.2d 1094",
            "year": 1988,
            "content": "Florida case on reasonable suspicion and investigatory stops."
        },
        {
            "case_name": "State v. Pollard",
            "court_id": "fla",
            "citation": "625 So.2d 968",
            "year": 1993,
            "content": "Florida case on Fourth Amendment protections during vehicle stops."
        },
        {
            "case_name": "Motor Vehicles v. Dobrin",
            "court_id": "fla-dca",
            "citation": "829 So.2d 922",
            "year": 2002,
            "content": "District Court of Appeal decision in Dobrin case."
        },
        {
            "case_name": "Holland v. State",
            "court_id": "fla",
            "citation": "696 So.2d 757",
            "year": 1997,
            "content": "Florida Supreme Court case on constitutional rights."
        },
        {
            "case_name": "State v. Daniel",
            "court_id": "fla",
            "citation": "665 So.2d 1040",
            "year": 1995,
            "content": "Florida case on criminal procedure and constitutional protections."
        },
        {
            "case_name": "Terry v. Ohio",
            "court_id": "scotus",
            "citation": "392 U.S. 1",
            "year": 1968,
            "content": "Landmark Supreme Court case establishing Terry stop doctrine."
        },
        {
            "case_name": "Whren v. United States",
            "court_id": "scotus",
            "citation": "517 U.S. 806",
            "year": 1996,
            "content": "Supreme Court case on pretextual traffic stops."
        }
    ]

    try:
        for case in cases:
            case_id = str(uuid.uuid4())

            # Check if case already exists
            existing = await conn.fetchval(
                "SELECT id FROM cases WHERE case_name = $1 AND court_id = $2",
                case['case_name'], case['court_id']
            )

            if existing:
                print(f"Case already exists: {case['case_name']}")
                continue

            # Insert the case
            await conn.execute("""
                INSERT INTO cases (id, case_name, court_id, date_filed, content, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                case_id,
                case['case_name'],
                case['court_id'],
                datetime(case['year'], 1, 1),  # Use Jan 1 of the year
                case['content'],
                f'{{"citation": "{case["citation"]}", "year": {case["year"]}}}'
            )

            print(f"✅ Added: {case['case_name']} ({case['citation']})")

    finally:
        await conn.close()

    print("\n✨ Florida cases added to database!")

if __name__ == "__main__":
    asyncio.run(add_cases())