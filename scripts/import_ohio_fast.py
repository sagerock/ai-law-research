#!/usr/bin/env python3
"""
Fast Ohio case import - imports metadata first, embeddings can be added later
"""

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

OHIO_COURTS = {
    'ohio': ('Ohio Supreme Court', 2000),
    'ohioctapp': ('Ohio Court of Appeals', 5000),
    'ca6': ('6th Circuit', 2000),
    'ohioctcl': ('Ohio Court of Claims', 500),
}

async def import_court_cases(conn, court_listener_id: str, court_name: str, limit: int):
    """Import cases from a specific court"""
    print(f"\n{'='*80}")
    print(f"📚 Importing {court_name} (limit: {limit:,})")
    print(f"{'='*80}")

    # Get the integer court_id from our database
    court_id = await conn.fetchval(
        "SELECT id FROM courts WHERE court_listener_id = $1",
        court_listener_id
    )

    if not court_id:
        print(f"  ❌ Court '{court_listener_id}' not found in database")
        return 0

    headers = {}
    if COURTLISTENER_TOKEN:
        headers["Authorization"] = f"Token {COURTLISTENER_TOKEN}"

    imported = 0
    skipped = 0
    page = 1

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        while imported < limit:
            try:
                print(f"  🔍 Page {page} ({imported:,}/{limit:,} imported, {skipped} skipped)...", end="", flush=True)

                response = await client.get(
                    "https://www.courtlistener.com/api/rest/v4/search/",
                    params={
                        "q": f"court_id:{court_listener_id}",
                        "type": "o",
                        "order_by": "dateFiled desc",
                        "page": page,
                        "page_size": 20
                    }
                )

                if response.status_code == 429:
                    print(" ⏳ Rate limited, waiting 60s...")
                    await asyncio.sleep(60)
                    continue

                if response.status_code != 200:
                    print(f" ❌ Error {response.status_code}")
                    break

                data = response.json()
                results = data.get('results', [])

                if not results:
                    print(" No more results")
                    break

                for case in results:
                    if imported >= limit:
                        break

                    # Use cluster_id as the primary ID (this is the case ID in CourtListener)
                    case_id = str(case.get('cluster_id', '')) or str(case.get('id', ''))
                    if not case_id or case_id == 'None':
                        continue

                    # Check if we already have this case
                    exists = await conn.fetchval(
                        "SELECT 1 FROM cases WHERE id = $1",
                        case_id
                    )

                    if exists:
                        skipped += 1
                        continue

                    # Import case metadata
                    case_name = case.get('caseName', 'Unknown')
                    date_filed = case.get('dateFiled')
                    snippet = case.get('snippet', '')
                    citation_count = case.get('citeCount', 0)

                    try:
                        await conn.execute("""
                            INSERT INTO cases (
                                id, title, court_id, decision_date,
                                content, citation_count, metadata, source_url
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (id) DO NOTHING
                        """,
                            case_id,
                            case_name[:200],
                            court_id,
                            datetime.fromisoformat(date_filed.replace('Z', '+00:00')) if date_filed else None,
                            snippet,
                            citation_count,
                            json.dumps({
                                'full_name': case.get('caseNameFull', case_name),
                                'court': case.get('court', ''),
                                'citations': case.get('citation', []),
                                'import_source': f'ohio_fast_{court_listener_id}'
                            }),
                            case.get('absolute_url', '')
                        )
                        imported += 1
                    except Exception as e:
                        print(f"\n  ❌ Error importing {case_name[:40]}: {e}")

                print(f" ✓")

                page += 1

                # Check if there are more pages
                if not data.get('next'):
                    print("  ℹ️  Reached end of results")
                    break

                # Small delay to be respectful
                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"\n  ❌ Error on page {page}: {e}")
                break

    print(f"\n✨ Imported {imported:,} cases from {court_name}")
    return imported

async def main():
    print("="*80)
    print("🏛️  OHIO LEGAL RESEARCH - FAST CASE IMPORT")
    print("="*80)
    print("\nImporting case metadata (embeddings can be added later)\n")

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Current stats
        total_before = await conn.fetchval("SELECT COUNT(*) FROM cases")
        print(f"📊 Current database: {total_before:,} cases\n")

        stats = {}

        # Import from each court
        for court_id, (court_name, limit) in OHIO_COURTS.items():
            stats[court_id] = await import_court_cases(conn, court_id, court_name, limit)

        # Final stats
        total_after = await conn.fetchval("SELECT COUNT(*) FROM cases")
        ohio_specific = await conn.fetchval("""
            SELECT COUNT(*) FROM cases
            WHERE court_id IN (
                SELECT id FROM courts
                WHERE court_listener_id IN ('ohio', 'ohioctapp', 'ohioctcl', 'ca6')
            )
        """)

        print("\n" + "="*80)
        print("📈 IMPORT SUMMARY")
        print("="*80)
        for court_id, (court_name, _) in OHIO_COURTS.items():
            print(f"  {court_name:30} {stats.get(court_id, 0):>6,} cases")
        print(f"  {'-'*42}")
        print(f"  {'Total imported:':30} {sum(stats.values()):>6,} cases")
        print(f"\n  Database size: {total_after:,} cases (+{total_after - total_before:,})")
        print(f"  Ohio cases: {ohio_specific:,} cases")

        # Show sample
        samples = await conn.fetch("""
            SELECT c.title, ct.name as court_name, c.decision_date, c.citation_count
            FROM cases c
            JOIN courts ct ON c.court_id = ct.id
            WHERE ct.court_listener_id IN ('ohio', 'ohioctapp', 'ohioctcl', 'ca6')
            ORDER BY c.citation_count DESC NULLS LAST
            LIMIT 10
        """)

        if samples:
            print(f"\n🏆 Top 10 Most-Cited Cases:")
            for i, row in enumerate(samples, 1):
                year = row['decision_date'].year if row['decision_date'] else 'N/A'
                cites = row['citation_count'] or 0
                print(f"  {i:2}. {row['title'][:50]:50} | {row['court_name'][:15]:15} | {year} | {cites:,}")

        print("\n" + "="*80)
        print("✅ IMPORT COMPLETE!")
        print("="*80)
        print("\nNext steps:")
        print("  1. Generate embeddings for semantic search (separate script)")
        print("  2. Test search functionality")
        print("  3. Add Ohio-specific UI filters")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
