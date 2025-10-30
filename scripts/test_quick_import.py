#!/usr/bin/env python3
"""Quick test to import a few Ohio Supreme Court cases"""

import asyncio
import asyncpg
import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_TOKEN")

async def test_import():
    print("Testing Ohio case import...")
    print(f"CourtListener Token: {'✓ Found' if COURTLISTENER_TOKEN else '✗ Missing'}\n")

    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)

    # Check Ohio Supreme Court court_id
    ohio_court = await conn.fetchrow(
        "SELECT id, court_listener_id, name FROM courts WHERE court_listener_id = 'ohio'"
    )
    print(f"Ohio Supreme Court in DB: id={ohio_court['id']}, name={ohio_court['name']}\n")

    # Try to fetch a few cases
    headers = {}
    if COURTLISTENER_TOKEN:
        headers["Authorization"] = f"Token {COURTLISTENER_TOKEN}"

    print("Fetching cases from CourtListener API...")
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.get(
            "https://www.courtlistener.com/api/rest/v4/search/",
            params={
                "q": "court_id:ohio",
                "type": "o",
                "order_by": "dateFiled desc",
                "page_size": 5
            }
        )

        print(f"API Response: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Found {data.get('count', 0)} total cases")
            print(f"Got {len(data.get('results', []))} results\n")

            for i, case in enumerate(data.get('results', [])[:3], 1):
                print(f"{i}. {case.get('caseName', 'N/A')}")
                print(f"   Court: {case.get('court', 'N/A')} (ID: {case.get('court_id', 'N/A')})")
                print(f"   Date: {case.get('dateFiled', 'N/A')}")
                print(f"   Opinion ID: {case.get('id', 'N/A')}\n")

                # Try to import this case
                court_listener_id = case.get('court_id', '')
                court_id = await conn.fetchval(
                    "SELECT id FROM courts WHERE court_listener_id = $1",
                    court_listener_id
                )

                case_id = str(case.get('id', ''))
                case_name = case.get('caseName', 'Unknown')
                date_filed = case.get('dateFiled')

                try:
                    await conn.execute("""
                        INSERT INTO cases (
                            id, title, court_id, decision_date, content, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title
                    """,
                        case_id,
                        case_name[:200],
                        court_id,
                        datetime.fromisoformat(date_filed.replace('Z', '+00:00')) if date_filed else None,
                        case.get('snippet', ''),
                        json.dumps({'import': 'test'})
                    )
                    print(f"   ✓ Imported to database\n")
                except Exception as e:
                    print(f"   ✗ Error: {e}\n")
        else:
            print(f"Error response: {response.text}")

    # Show current database stats
    case_count = await conn.fetchval("SELECT COUNT(*) FROM cases")
    ohio_count = await conn.fetchval(
        "SELECT COUNT(*) FROM cases WHERE court_id = $1",
        ohio_court['id']
    )
    print(f"\nDatabase stats:")
    print(f"  Total cases: {case_count}")
    print(f"  Ohio cases: {ohio_count}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_import())
