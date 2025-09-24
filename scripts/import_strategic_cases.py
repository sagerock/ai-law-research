#!/usr/bin/env python3
"""
Strategic import of top-cited Supreme Court cases and recent appellate decisions.
This builds a focused, high-quality dataset for the legal research tool.
"""

import asyncio
import asyncpg
import httpx
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_TOKEN")

async def fetch_and_import_case(conn, case_data: dict, client: httpx.AsyncClient, source: str = "search"):
    """Import a single case with full opinion text"""

    case_id = str(case_data.get("id", ""))
    case_name = case_data.get("caseName", "Unknown Case")
    case_name_full = case_data.get("caseNameFull", case_name)
    court = case_data.get("court", "Unknown")
    court_id = case_data.get("court_id", "")
    date_filed = case_data.get("dateFiled")
    citation_count = case_data.get("citeCount", 0)
    absolute_url = case_data.get("absolute_url", "")

    # Skip if we already have this case with substantial content
    existing = await conn.fetchrow(
        "SELECT id, LENGTH(content) as content_length FROM cases WHERE id = $1",
        case_id
    )

    if existing and existing['content_length'] > 5000:
        print(f"  ✓ Already have {case_name[:50]} with {existing['content_length']} chars")
        return False

    # Get snippet/preview text
    snippet = case_data.get("snippet", "")

    # Try to get the opinion ID from the result
    opinion_id = case_data.get("opinion_id") or case_data.get("id")

    print(f"  📥 Fetching: {case_name[:60]}")

    # Try direct opinion endpoint
    full_text = snippet
    if opinion_id:
        opinion_url = f"https://www.courtlistener.com/api/rest/v3/opinions/{opinion_id}/"
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
        except Exception as e:
            print(f"    ⚠️  Could not fetch full opinion: {e}")

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
                }
            )

            if embed_response.status_code == 200:
                embedding_data = embed_response.json()["data"][0]["embedding"]
                embedding = '[' + ','.join(map(str, embedding_data)) + ']'
        except Exception as e:
            print(f"    ⚠️  Embedding error: {e}")

    # Get citations
    citations = case_data.get("citation", [])
    citation_str = "; ".join(citations) if citations else ""

    # Store in database
    await conn.execute("""
        INSERT INTO cases (
            id, case_name, court_id, date_filed,
            citation_count, url, content, embedding, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector, $9)
        ON CONFLICT (id) DO UPDATE SET
            case_name = EXCLUDED.case_name,
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

    print(f"  ✅ Imported: {case_name[:50]} ({len(content)} chars, {citation_count} cites)")
    return True

async def import_top_cited_supreme_court_cases(conn, limit=500):
    """Import the most-cited Supreme Court cases"""
    print(f"\n📚 Importing top {limit} most-cited Supreme Court cases...")

    headers = {
        "Authorization": f"Token {COURTLISTENER_TOKEN}"
    }

    imported_count = 0
    page = 1
    per_page = 20

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        while imported_count < limit:
            # Search for Supreme Court cases ordered by citation count
            search_url = "https://www.courtlistener.com/api/rest/v3/search/"
            params = {
                "q": "",  # Empty query to get all
                "type": "o",  # opinions
                "court": "scotus",  # Supreme Court of the United States
                "order_by": "citeCount desc",
                "page": page
            }

            try:
                print(f"\n  🔍 Fetching page {page}...")
                response = await client.get(search_url, params=params)

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

                    success = await fetch_and_import_case(conn, case_data, client, "top_cited_scotus")
                    if success:
                        imported_count += 1
                        await asyncio.sleep(0.5)  # Rate limiting

                page += 1

                # Check if there are more pages
                if not data.get("next"):
                    break

            except Exception as e:
                print(f"  ❌ Error on page {page}: {e}")
                break

    print(f"\n✨ Imported {imported_count} top-cited Supreme Court cases")
    return imported_count

async def import_recent_appellate_decisions(conn, months_back=24):
    """Import recent appellate court decisions"""
    print(f"\n⚖️  Importing appellate decisions from the last {months_back} months...")

    headers = {
        "Authorization": f"Token {COURTLISTENER_TOKEN}"
    }

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)

    # List of appellate courts to import from
    appellate_courts = [
        "ca1",  # First Circuit
        "ca2",  # Second Circuit
        "ca3",  # Third Circuit
        "ca4",  # Fourth Circuit
        "ca5",  # Fifth Circuit
        "ca6",  # Sixth Circuit
        "ca7",  # Seventh Circuit
        "ca8",  # Eighth Circuit
        "ca9",  # Ninth Circuit
        "ca10", # Tenth Circuit
        "ca11", # Eleventh Circuit
        "cadc", # D.C. Circuit
        "cafc", # Federal Circuit
    ]

    imported_count = 0

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for court in appellate_courts:
            print(f"\n  🏛️  Importing from {court}...")

            # Search for recent cases from this court
            search_url = "https://www.courtlistener.com/api/rest/v3/search/"
            params = {
                "q": "",
                "type": "o",
                "court": court,
                "filed_after": start_date.strftime("%Y-%m-%d"),
                "order_by": "dateFiled desc",
                "page": 1
            }

            try:
                response = await client.get(search_url, params=params)

                if response.status_code != 200:
                    print(f"    ❌ Search failed for {court}: {response.status_code}")
                    continue

                data = response.json()
                results = data.get("results", [])[:10]  # Get up to 10 recent cases per court

                for case_data in results:
                    success = await fetch_and_import_case(conn, case_data, client, f"recent_{court}")
                    if success:
                        imported_count += 1
                        await asyncio.sleep(0.5)  # Rate limiting

            except Exception as e:
                print(f"    ❌ Error importing from {court}: {e}")

    print(f"\n✨ Imported {imported_count} recent appellate decisions")
    return imported_count

async def main():
    print("=" * 60)
    print("Strategic Case Import - Building Quality Dataset")
    print("=" * 60)

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Get current stats
        total_before = await conn.fetchval("SELECT COUNT(*) FROM cases")
        with_content_before = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE LENGTH(content) > 1000")

        print(f"\n📊 Current database stats:")
        print(f"  Total cases: {total_before}")
        print(f"  Cases with content: {with_content_before}")

        # Import top-cited Supreme Court cases
        scotus_count = await import_top_cited_supreme_court_cases(conn, limit=500)

        # Import recent appellate decisions
        appellate_count = await import_recent_appellate_decisions(conn, months_back=24)

        # Get final stats
        total_after = await conn.fetchval("SELECT COUNT(*) FROM cases")
        with_content_after = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE LENGTH(content) > 1000")

        print("\n" + "=" * 60)
        print("📈 Import Summary")
        print("=" * 60)
        print(f"  Supreme Court cases imported: {scotus_count}")
        print(f"  Appellate cases imported: {appellate_count}")
        print(f"  Total cases now: {total_after} (+{total_after - total_before})")
        print(f"  Cases with content: {with_content_after} (+{with_content_after - with_content_before})")

        # Show some top cases
        top_cases = await conn.fetch("""
            SELECT case_name, court_id, citation_count, LENGTH(content) as content_length
            FROM cases
            WHERE citation_count IS NOT NULL
            ORDER BY citation_count DESC
            LIMIT 10
        """)

        if top_cases:
            print("\n🏆 Top 10 Most-Cited Cases in Database:")
            for i, row in enumerate(top_cases, 1):
                print(f"  {i:2}. {row['case_name'][:40]:40} | {row['court_id']:6} | {row['citation_count']:,} cites | {row['content_length']:,} chars")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())