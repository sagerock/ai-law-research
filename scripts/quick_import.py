#!/usr/bin/env python3

"""
Quick import of sample data from CourtListener
Works with anonymous API access
"""

import asyncio
import asyncpg
import httpx
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def setup_database():
    """Verify database tables exist (tables should be created by migration)"""
    conn = await asyncpg.connect(DATABASE_URL)

    # Just verify the tables exist
    try:
        await conn.fetchval("SELECT 1 FROM courts LIMIT 1")
        await conn.fetchval("SELECT 1 FROM cases LIMIT 1")
        print("✓ Database tables ready")
    except Exception as e:
        print(f"⚠ Warning: Tables may not exist. Run migrations first. Error: {e}")

    await conn.close()

async def import_courts():
    """Import court data"""
    print("\nImporting courts...")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.courtlistener.com/api/rest/v4/courts/",
            params={"page_size": 100}
        )

        if response.status_code == 200:
            data = response.json()
            courts = data["results"]

            conn = await asyncpg.connect(DATABASE_URL)

            for court in courts:
                await conn.execute("""
                    INSERT INTO courts (court_listener_id, name, full_name, jurisdiction, url)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (court_listener_id) DO UPDATE SET
                        full_name = EXCLUDED.full_name
                """,
                    court["id"],
                    court["short_name"],
                    court["full_name"],
                    court.get("jurisdiction", ""),
                    court["url"]
                )

            await conn.close()
            print(f"✓ Imported {len(courts)} courts")
            return True

    return False

async def search_and_import_cases():
    """Search for cases and import metadata"""
    print("\nSearching for recent important cases...")

    queries = [
        "personal jurisdiction",
        "qualified immunity",
        "summary judgment",
        "class action certification"
    ]

    conn = await asyncpg.connect(DATABASE_URL)
    total_cases = 0

    for query in queries:
        print(f"  Searching: {query}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.courtlistener.com/api/rest/v4/search/",
                params={
                    "q": query,
                    "type": "o",
                    "order_by": "score desc",
                    "page_size": 10
                }
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                for result in results:
                    # Extract available metadata - use cluster_id as the case ID
                    case_id = str(result.get("cluster_id", ""))

                    # Skip if no valid ID
                    if not case_id or case_id == "":
                        continue

                    case_name = result.get("caseName", "Unknown")
                    court_cl_id = result.get("court_id", "")  # This is CourtListener court ID
                    date_filed = result.get("dateFiled")
                    citation_count = result.get("citeCount", 0)
                    url = result.get("absolute_url", "")
                    # Get snippet from syllabus or first part of case
                    snippet = result.get("syllabus", "")[:1000] if result.get("syllabus") else ""

                    # Look up the court's integer ID from our courts table
                    court_id = None
                    if court_cl_id:
                        court_id = await conn.fetchval(
                            "SELECT id FROM courts WHERE court_listener_id = $1",
                            court_cl_id
                        )

                    # Generate embedding if we have content
                    embedding = None
                    if OPENAI_API_KEY and snippet:
                        embedding_list = await generate_embedding(snippet)
                        if embedding_list:
                            # Convert list to PostgreSQL vector string format
                            embedding = '[' + ','.join(map(str, embedding_list)) + ']'

                    try:
                        # Store case - use title column (required by migration) instead of case_name
                        await conn.execute("""
                            INSERT INTO cases (
                                id, title, court_id, decision_date,
                                content, embedding, metadata, source_url
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (id) DO UPDATE SET
                                content = EXCLUDED.content
                        """,
                            case_id,
                            case_name,
                            court_id,
                            datetime.strptime(date_filed, "%Y-%m-%d") if date_filed else None,
                            snippet,
                            embedding,
                            json.dumps(result),
                            url
                        )
                        total_cases += 1
                    except Exception as e:
                        print(f"    ⚠ Failed to import case {case_id}: {e}")

    await conn.close()
    print(f"✓ Imported {total_cases} case records")

async def import_citations():
    """Import some citation relationships"""
    print("\nImporting citation graph...")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.courtlistener.com/api/rest/v4/opinions-cited/",
            params={"page_size": 100}
        )

        if response.status_code == 200:
            data = response.json()
            citations = data["results"]

            conn = await asyncpg.connect(DATABASE_URL)

            for cite in citations[:100]:  # First 100 citations
                try:
                    await conn.execute("""
                        INSERT INTO citations (source_case_id, target_case_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """,
                        str(cite.get("citing_opinion", "")),
                        str(cite.get("cited_opinion", ""))
                    )
                except:
                    # Skip citations that don't have valid case IDs
                    pass

            await conn.close()
            print(f"✓ Imported {len(citations[:100])} citations")

async def generate_embedding(text):
    """Generate embedding using OpenAI"""
    if not OPENAI_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "input": text[:8000],
                    "model": "text-embedding-3-small"
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json()["data"][0]["embedding"]
    except:
        pass

    return None

async def show_summary():
    """Show what we imported"""
    conn = await asyncpg.connect(DATABASE_URL)

    court_count = await conn.fetchval("SELECT COUNT(*) FROM courts")
    case_count = await conn.fetchval("SELECT COUNT(*) FROM cases")
    citation_count = await conn.fetchval("SELECT COUNT(*) FROM citations")

    print("\n" + "="*50)
    print("IMPORT SUMMARY")
    print("="*50)
    print(f"Courts: {court_count:,}")
    print(f"Cases: {case_count:,}")
    print(f"Citations: {citation_count:,}")

    # Show sample cases
    print("\nSample cases imported:")
    rows = await conn.fetch("""
        SELECT title, decision_date
        FROM cases
        WHERE title != 'Unknown'
        ORDER BY created_at DESC
        LIMIT 5
    """)

    for row in rows:
        date_str = row['decision_date'].strftime('%Y-%m-%d') if row['decision_date'] else 'N/A'
        print(f"  • {row['title'][:60]}")
        print(f"    Decision date: {date_str}")

    await conn.close()

async def main():
    """Run quick import"""
    print("""
╔══════════════════════════════════════════════╗
║        Quick Data Import from CourtListener    ║
╚══════════════════════════════════════════════╝
    """)

    try:
        # Setup
        await setup_database()

        # Import data
        await import_courts()
        await search_and_import_cases()
        await import_citations()

        # Summary
        await show_summary()

        print("\n✅ Quick import complete!")
        print("\nYou now have sample data to test with.")

    except Exception as e:
        print(f"\n❌ Import failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())