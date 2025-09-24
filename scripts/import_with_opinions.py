#!/usr/bin/env python3
"""
Import cases with full opinion text from CourtListener
This fetches the full opinion content for each case
"""

import asyncio
import asyncpg
import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import sys

load_dotenv()

DATABASE_URL = "postgresql://legal_user:legal_pass@localhost:5432/legal_research"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Popular Supreme Court cases that likely have full opinions
LANDMARK_CASES = [
    "Brown v. Board of Education",
    "Miranda v. Arizona",
    "Roe v. Wade",
    "Citizens United",
    "Obergefell v. Hodges",
    "Marbury v. Madison",
    "McCulloch v. Maryland",
    "Gideon v. Wainwright",
    "New York Times v. Sullivan",
    "Mapp v. Ohio"
]

async def fetch_opinion_text(case_id: str, absolute_url: str, client: httpx.AsyncClient) -> str:
    """Fetch the full opinion text for a case"""
    # Try to fetch from the opinion endpoint with authentication
    if absolute_url:
        opinion_url = f"https://www.courtlistener.com/api/rest/v3{absolute_url}"
        try:
            response = await client.get(opinion_url)
            if response.status_code == 200:
                data = response.json()
                # Look for various text fields
                return (
                    data.get("plain_text", "") or
                    data.get("html", "") or
                    data.get("html_with_citations", "") or
                    data.get("xml_harvard", "") or
                    ""
                )
        except Exception as e:
            print(f"    Failed to fetch opinion: {e}")
    return ""

async def search_and_import_case(conn, search_query: str):
    """Search for a case and import it with full opinion text"""
    print(f"\n🔍 Searching for: {search_query}")

    # CourtListener API token
    # Get CourtListener token from environment
    courtlistener_token = os.getenv("COURTLISTENER_TOKEN")
    if not courtlistener_token:
        print("Error: COURTLISTENER_TOKEN not found in environment variables")
        return False

    headers = {
        "Authorization": f"Token {courtlistener_token}"
    }

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Search for the case
        search_url = "https://www.courtlistener.com/api/rest/v3/search/"
        params = {
            "q": search_query,
            "type": "o",  # opinions
            "order_by": "score desc"
        }

        try:
            response = await client.get(search_url, params=params)
            if response.status_code != 200:
                print(f"  ❌ Search failed: {response.status_code}")
                return False

            data = response.json()
            results = data.get("results", [])

            if not results:
                print(f"  ❌ No results found")
                return False

            # Process first result
            result = results[0]
            case_id = str(result.get("id", ""))
            case_name = result.get("caseName", search_query)
            case_name_full = result.get("caseNameFull", case_name)
            court = result.get("court", "Unknown")
            court_id = result.get("court_id", "")
            date_filed = result.get("dateFiled")
            citation_count = result.get("citeCount", 0)
            docket_number = result.get("docketNumber", "")
            judge = result.get("judge", "")
            absolute_url = result.get("absolute_url", "")

            # Get snippet/preview text
            snippet = result.get("snippet", "")

            # Try to get the opinion ID from the result
            opinion_id = result.get("opinion_id") or result.get("id")

            # Fetch full opinion text via API
            print(f"  📥 Fetching full opinion for {case_name[:50]}...")

            # Try direct opinion endpoint
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
                    else:
                        full_text = snippet
                except Exception as e:
                    print(f"    ⚠️  Could not fetch full opinion: {e}")
                    full_text = snippet
            else:
                full_text = snippet

            # If we still don't have much text, try the download URL
            if len(full_text) < 500 and result.get("download_url"):
                try:
                    download_url = f"https://www.courtlistener.com{result.get('download_url')}"
                    dl_response = await client.get(download_url)
                    if dl_response.status_code == 200:
                        full_text = dl_response.text
                except:
                    pass

            # Clean up the text
            if full_text:
                # Remove excessive whitespace
                full_text = ' '.join(full_text.split())
                # Limit to reasonable size
                full_text = full_text[:50000]  # ~50KB of text

            content = full_text or snippet or f"{case_name_full}. {court}."

            print(f"  📝 Got {len(content)} characters of content")

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
                        print(f"  ✓ Generated embedding")
                except Exception as e:
                    print(f"  ⚠️  Embedding error: {e}")

            # Get citations
            citations = result.get("citation", [])
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
                    "docket": docket_number,
                    "judge": judge,
                    "citations": citations,
                    "citation": citation_str
                })
            )

            print(f"  ✅ Imported: {case_name[:60]} ({len(content)} chars)")
            return True

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    print("=" * 60)
    print("CourtListener Bulk Import with Full Opinions")
    print("=" * 60)

    conn = await asyncpg.connect(DATABASE_URL)

    # Import landmark cases with full opinions
    success_count = 0
    for case_name in LANDMARK_CASES:
        if await search_and_import_case(conn, case_name):
            success_count += 1
            await asyncio.sleep(1)  # Rate limiting

    print(f"\n✨ Successfully imported {success_count} cases with full opinions")

    # Show what we have
    count = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE LENGTH(content) > 1000")
    print(f"📚 Total cases with substantial content (>1000 chars): {count}")

    # Show a sample
    sample = await conn.fetch("""
        SELECT case_name, LENGTH(content) as content_length
        FROM cases
        WHERE LENGTH(content) > 1000
        ORDER BY content_length DESC
        LIMIT 5
    """)

    if sample:
        print("\n📊 Sample cases with full content:")
        for row in sample:
            print(f"  - {row['case_name'][:50]:50} | {row['content_length']:,} chars")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())