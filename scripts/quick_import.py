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
    """Create tables if they don't exist"""
    conn = await asyncpg.connect(DATABASE_URL)

    await conn.execute("""
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS courts (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            full_name TEXT,
            jurisdiction TEXT,
            level TEXT,
            abbreviation TEXT,
            court_listener_id TEXT UNIQUE,
            url TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            court_id TEXT,
            case_name TEXT,
            date_filed DATE,
            citation_count INTEGER,
            url TEXT,
            content TEXT,
            embedding vector(1536),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS citations (
            id SERIAL PRIMARY KEY,
            citing_opinion TEXT,
            cited_opinion TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    await conn.close()
    print("✓ Database tables ready")

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
                results = data["results"]

                for result in results:
                    # Extract available metadata
                    case_id = str(result.get("id", ""))
                    case_name = result.get("caseName", "Unknown")
                    court = result.get("court", "")
                    date_filed = result.get("dateFiled")
                    citation_count = result.get("citeCount", 0)
                    url = result.get("absolute_url", "")
                    snippet = result.get("snippet", "")

                    # Generate embedding if we have content
                    embedding = None
                    if OPENAI_API_KEY and snippet:
                        embedding = await generate_embedding(snippet)

                    # Store case
                    await conn.execute("""
                        INSERT INTO cases (
                            id, case_name, court_id, date_filed,
                            citation_count, url, content, embedding, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (id) DO UPDATE SET
                            citation_count = EXCLUDED.citation_count
                    """,
                        case_id,
                        case_name,
                        court,
                        datetime.strptime(date_filed, "%Y-%m-%d") if date_filed else None,
                        citation_count,
                        url,
                        snippet,
                        embedding,
                        json.dumps(result)
                    )

                    total_cases += 1

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
                await conn.execute("""
                    INSERT INTO citations (citing_opinion, cited_opinion)
                    VALUES ($1, $2)
                """,
                    str(cite.get("citing_opinion", "")),
                    str(cite.get("cited_opinion", ""))
                )

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
        SELECT case_name, date_filed, citation_count
        FROM cases
        WHERE case_name != 'Unknown'
        ORDER BY citation_count DESC NULLS LAST
        LIMIT 5
    """)

    for row in rows:
        date_str = row['date_filed'].strftime('%Y-%m-%d') if row['date_filed'] else 'N/A'
        print(f"  • {row['case_name'][:60]}")
        print(f"    Filed: {date_str}, Citations: {row['citation_count'] or 0}")

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