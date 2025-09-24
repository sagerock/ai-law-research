#!/usr/bin/env python3
import asyncpg
import asyncio

async def check():
    conn = await asyncpg.connect('postgresql://legal_user:legal_pass@localhost:5432/legal_research')

    # Check cases
    cases = await conn.fetch("SELECT * FROM cases LIMIT 5")
    print(f"Cases found: {len(cases)}")
    for case in cases:
        print(f"  - {case['case_name'][:50] if case['case_name'] else 'No name'}")
        print(f"    Content: {case['content'][:100] if case['content'] else 'No content'}...")

    # Check courts
    courts = await conn.fetch("SELECT * FROM courts LIMIT 5")
    print(f"\nCourts found: {len(courts)}")
    for court in courts:
        print(f"  - {court['name']}: {court['full_name'][:50] if court['full_name'] else ''}")

    await conn.close()

asyncio.run(check())