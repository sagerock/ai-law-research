#!/usr/bin/env python3
"""
Import Ohio cases from CourtListener to build a comprehensive Ohio legal research database.

This script imports cases from:
- Ohio Supreme Court (court_id: ohio)
- Ohio Court of Appeals (court_id: ohioctapp)
- Ohio Court of Claims (court_id: ohioctcl)
- 6th Circuit Court of Appeals (court_id: ca6) - covers Ohio federal cases

Target: 10,000+ Ohio cases for comprehensive coverage
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_TOKEN")

# Ohio courts in CourtListener
OHIO_COURTS = {
    'ohio': 'Ohio Supreme Court',
    'ohioctapp': 'Ohio Court of Appeals',
    'ohioctcl': 'Ohio Court of Claims',
    'ca6': '6th Circuit Court of Appeals (covers Ohio)',
}

async def fetch_and_import_case(conn, case_data: dict, client: httpx.AsyncClient, source: str = "ohio"):
    """Import a single case with full opinion text"""

    case_id = str(case_data.get("id", ""))
    if not case_id:
        return False

    case_name = case_data.get("caseName", "Unknown Case")
    case_name_full = case_data.get("caseNameFull", case_name)
    court = case_data.get("court", "Unknown")
    court_listener_id = case_data.get("court_id", "")

    # Look up the integer court_id from our courts table
    court_id = None
    if court_listener_id:
        court_id = await conn.fetchval(
            "SELECT id FROM courts WHERE court_listener_id = $1",
            court_listener_id
        )
    date_filed = case_data.get("dateFiled")
    citation_count = case_data.get("citeCount", 0)
    absolute_url = case_data.get("absolute_url", "")

    # Skip if we already have this case with substantial content
    existing = await conn.fetchrow(
        "SELECT id, LENGTH(content) as content_length FROM cases WHERE id = $1",
        case_id
    )

    if existing and existing['content_length'] > 5000:
        return False

    # Get snippet/preview text
    snippet = case_data.get("snippet", "")

    # Try to get the opinion ID from the result
    opinion_id = case_data.get("opinion_id") or case_data.get("id")

    # Try direct opinion endpoint for full text
    full_text = snippet
    if opinion_id:
        opinion_url = f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/"
        try:
            op_response = await client.get(opinion_url)
            if op_response.status_code == 200:
                opinion_data = op_response.json()
                full_text = (
                    opinion_data.get("plain_text", "") or
                    opinion_data.get("html_lawbox", "") or
                    opinion_data.get("html", "") or
                    opinion_data.get("html_with_citations", "") or
                    snippet
                )
        except Exception:
            pass

    # If we still don't have much text, try the download URL
    if len(full_text) < 500 and case_data.get("download_url"):
        try:
            download_url = f"https://www.courtlistener.com{case_data.get('download_url')}"
            dl_response = await client.get(download_url)
            if dl_response.status_code == 200:
                full_text = dl_response.text
        except:
            pass

    # Clean up the text
    if full_text:
        full_text = ' '.join(full_text.split())
        full_text = full_text[:100000]  # Limit to 100KB

    content = full_text or snippet or f"{case_name_full}. {court}."

    # Generate embedding if we have substantial content
    embedding = None
    if OPENAI_API_KEY and len(content) > 100:
        try:
            embed_response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "input": content[:8000],
                    "model": "text-embedding-3-small"
                },
                timeout=30.0
            )

            if embed_response.status_code == 200:
                embedding_data = embed_response.json()["data"][0]["embedding"]
                embedding = '[' + ','.join(map(str, embedding_data)) + ']'
        except Exception:
            pass

    # Get citations
    citations = case_data.get("citation", [])
    citation_str = "; ".join(citations) if citations else ""

    # Store in database
    try:
        await conn.execute("""
            INSERT INTO cases (
                id, title, court_id, decision_date,
                citation_count, source_url, content, embedding, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector, $9)
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                citation_count = EXCLUDED.citation_count,
                metadata = EXCLUDED.metadata
        """,
            case_id,
            case_name[:200],
            court_id,
            datetime.fromisoformat(date_filed.replace('Z', '+00:00')) if date_filed else None,
            citation_count,
            absolute_url,
            content,
            embedding,
            json.dumps({
                "full_name": case_name_full,
                "court": court,
                "citations": citations,
                "citation": citation_str,
                "import_source": source
            })
        )
        return True
    except Exception as e:
        print(f"    ❌ Error importing {case_name[:40]}: {e}")
        return False

async def import_from_court(conn, court_id: str, court_name: str, limit: int = 1000):
    """Import cases from a specific Ohio court"""
    print(f"\n{'='*80}")
    print(f"📚 Importing {court_name} (court_id: {court_id})")
    print(f"{'='*80}")

    headers = {}
    if COURTLISTENER_TOKEN:
        headers["Authorization"] = f"Token {COURTLISTENER_TOKEN}"

    imported_count = 0
    page = 1

    async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
        while imported_count < limit:
            # Search for cases from this court
            search_url = "https://www.courtlistener.com/api/rest/v4/search/"
            params = {
                "q": f"court_id:{court_id}",
                "type": "o",  # opinions
                "order_by": "dateFiled desc",  # Most recent first
                "page": page
            }

            try:
                print(f"\n  🔍 Fetching page {page} ({imported_count}/{limit} imported so far)...")
                response = await client.get(search_url, params=params)

                if response.status_code == 429:
                    print(f"  ⏳ Rate limited. Waiting 60 seconds...")
                    await asyncio.sleep(60)
                    continue

                if response.status_code != 200:
                    print(f"  ❌ Search failed: {response.status_code}")
                    break

                data = response.json()
                results = data.get("results", [])

                if not results:
                    print(f"  ℹ️  No more results")
                    break

                # Process each case
                for case_data in results:
                    if imported_count >= limit:
                        break

                    success = await fetch_and_import_case(conn, case_data, client, f"ohio_{court_id}")
                    if success:
                        imported_count += 1
                        if imported_count % 10 == 0:
                            print(f"  ✅ Progress: {imported_count}/{limit} cases imported")

                    # Rate limiting - be respectful
                    await asyncio.sleep(0.5)

                page += 1

                # Check if there are more pages
                if not data.get("next"):
                    print(f"  ℹ️  Reached end of results")
                    break

            except Exception as e:
                print(f"  ❌ Error on page {page}: {e}")
                break

    print(f"\n✨ Imported {imported_count} cases from {court_name}")
    return imported_count

async def main():
    """Main import process"""
    print("=" * 80)
    print("🏛️  OHIO LEGAL RESEARCH DATABASE - CASE IMPORT")
    print("=" * 80)
    print("\nBuilding comprehensive Ohio case coverage for solo practitioners")
    print("and small law firms.\n")

    if not COURTLISTENER_TOKEN:
        print("⚠️  WARNING: No COURTLISTENER_TOKEN found in environment")
        print("   You may hit rate limits quickly. Get a free token at:")
        print("   https://www.courtlistener.com/help/api/\n")

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Get current stats
        total_before = await conn.fetchval("SELECT COUNT(*) FROM cases")
        with_content_before = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE LENGTH(content) > 1000")

        print(f"📊 Current database stats:")
        print(f"  Total cases: {total_before:,}")
        print(f"  Cases with content: {with_content_before:,}\n")

        # Import strategy:
        # 1. Ohio Supreme Court - most important (2000 cases)
        # 2. Ohio Court of Appeals - high volume (5000 cases)
        # 3. 6th Circuit - federal cases (2000 cases)
        # 4. Ohio Court of Claims - specialized (500 cases)
        # Total target: ~10,000 cases

        stats = {}

        # Import Ohio Supreme Court
        stats['ohio'] = await import_from_court(
            conn, 'ohio', 'Ohio Supreme Court', limit=2000
        )

        # Import Ohio Court of Appeals
        stats['ohioctapp'] = await import_from_court(
            conn, 'ohioctapp', 'Ohio Court of Appeals', limit=5000
        )

        # Import 6th Circuit
        stats['ca6'] = await import_from_court(
            conn, 'ca6', '6th Circuit (covers Ohio)', limit=2000
        )

        # Import Ohio Court of Claims
        stats['ohioctcl'] = await import_from_court(
            conn, 'ohioctcl', 'Ohio Court of Claims', limit=500
        )

        # Get final stats
        total_after = await conn.fetchval("SELECT COUNT(*) FROM cases")
        with_content_after = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE LENGTH(content) > 1000")

        # Get Ohio-specific stats
        ohio_cases = await conn.fetchval("""
            SELECT COUNT(*) FROM cases
            WHERE court_id IN ('ohio', 'ohioctapp', 'ohioctcl', 'ca6')
        """)

        print("\n" + "=" * 80)
        print("📈 IMPORT SUMMARY")
        print("=" * 80)
        print(f"\n  Ohio Supreme Court:      {stats.get('ohio', 0):,} cases")
        print(f"  Ohio Court of Appeals:   {stats.get('ohioctapp', 0):,} cases")
        print(f"  6th Circuit:             {stats.get('ca6', 0):,} cases")
        print(f"  Ohio Court of Claims:    {stats.get('ohioctcl', 0):,} cases")
        print(f"  {'-'*50}")
        print(f"  Total imported:          {sum(stats.values()):,} cases")
        print(f"\n  Total database size:     {total_after:,} cases (+{total_after - total_before:,})")
        print(f"  Cases with content:      {with_content_after:,} (+{with_content_after - with_content_before:,})")
        print(f"  Ohio-specific cases:     {ohio_cases:,} cases")

        # Show some sample cases
        samples = await conn.fetch("""
            SELECT title, court_id, decision_date, citation_count, LENGTH(content) as content_length
            FROM cases
            WHERE court_id IN ('ohio', 'ohioctapp', 'ohioctcl', 'ca6')
            ORDER BY citation_count DESC NULLS LAST
            LIMIT 10
        """)

        if samples:
            print(f"\n🏆 Top 10 Most-Cited Ohio Cases in Database:")
            for i, row in enumerate(samples, 1):
                date_str = row['decision_date'].strftime('%Y') if row['decision_date'] else 'N/A'
                cites = row['citation_count'] or 0
                print(f"  {i:2}. {row['title'][:45]:45} | {row['court_id']:10} | {date_str} | {cites:,} cites")

        print("\n" + "=" * 80)
        print("✅ Import Complete!")
        print("=" * 80)
        print("\nYour Ohio legal research database is ready.")
        print("Next steps:")
        print("  1. Test search functionality with Ohio cases")
        print("  2. Add Ohio-specific filters to the UI")
        print("  3. Consider importing older cases for historical coverage")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
