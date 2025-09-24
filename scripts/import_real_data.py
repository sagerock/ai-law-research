#!/usr/bin/env python3

"""
Import real case data from CourtListener Search API
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

async def import_cases_from_search():
    """Import cases using the search API"""
    print("Importing real case data from CourtListener...")

    conn = await asyncpg.connect(DATABASE_URL)

    # Search queries to get diverse cases
    queries = [
        "personal jurisdiction",
        "qualified immunity",
        "summary judgment",
        "constitutional law",
        "contract breach"
    ]

    total_imported = 0

    for query in queries:
        print(f"\nSearching for: {query}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://www.courtlistener.com/api/rest/v4/search/",
                params={
                    "q": query,
                    "type": "o",
                    "page_size": 20,
                    "order_by": "score desc"
                }
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                for result in results:
                    try:
                        # Extract case data
                        case_id = str(result.get("cluster_id", ""))
                        case_name = result.get("caseName", "Unknown Case")
                        case_name_full = result.get("caseNameFull", case_name)
                        court = result.get("court", "Unknown")
                        court_id = result.get("court_id", "")
                        date_filed = result.get("dateFiled")
                        citation_count = result.get("citeCount", 0)
                        docket_number = result.get("docketNumber", "")
                        judge = result.get("judge", "")
                        url = result.get("absolute_url", "")

                        # Get citations
                        citations = result.get("citation", [])
                        citation_str = "; ".join(citations) if citations else ""

                        # Build content from available text
                        snippet = result.get("snippet", "")
                        text = result.get("text", "")
                        content = text or snippet or f"{case_name_full}. {citation_str}"

                        # Generate embedding if we have content
                        embedding = None
                        if OPENAI_API_KEY and content:
                            try:
                                async with httpx.AsyncClient(timeout=30.0) as embed_client:
                                    embed_response = await embed_client.post(
                                        "https://api.openai.com/v1/embeddings",
                                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                                        json={
                                            "input": content[:8000],
                                            "model": "text-embedding-3-small"
                                        }
                                    )

                                    if embed_response.status_code == 200:
                                        embedding_data = embed_response.json()["data"][0]["embedding"]
                                        # Format as PostgreSQL array
                                        embedding = '[' + ','.join(map(str, embedding_data)) + ']'
                            except Exception as e:
                                print(f"  Embedding error: {e}")

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
                                citation_count = EXCLUDED.citation_count
                        """,
                            case_id,
                            case_name[:200],  # Truncate long names
                            court_id,
                            datetime.strptime(date_filed, "%Y-%m-%d") if date_filed else None,
                            citation_count,
                            url,
                            content,
                            embedding,
                            json.dumps({
                                "full_name": case_name_full,
                                "court": court,
                                "docket": docket_number,
                                "judge": judge,
                                "citations": citations
                            })
                        )

                        total_imported += 1
                        print(f"  ✓ {case_name[:50]}")

                    except Exception as e:
                        print(f"  ✗ Error importing case: {e}")

    await conn.close()
    print(f"\n✅ Imported {total_imported} cases total")
    return total_imported

async def show_results():
    """Show what we imported"""
    conn = await asyncpg.connect(DATABASE_URL)

    # Statistics
    total_cases = await conn.fetchval("SELECT COUNT(*) FROM cases")
    cases_with_content = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE content IS NOT NULL AND content != ''")
    cases_with_embeddings = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE embedding IS NOT NULL")

    print("\n" + "="*50)
    print("IMPORT RESULTS")
    print("="*50)
    print(f"Total cases: {total_cases}")
    print(f"Cases with content: {cases_with_content}")
    print(f"Cases with embeddings: {cases_with_embeddings}")

    # Sample cases
    print("\nSample imported cases:")
    samples = await conn.fetch("""
        SELECT case_name, date_filed, citation_count,
               LENGTH(content) as content_length
        FROM cases
        WHERE content IS NOT NULL AND content != ''
        ORDER BY citation_count DESC NULLS LAST
        LIMIT 5
    """)

    for row in samples:
        date_str = row['date_filed'].strftime('%Y-%m-%d') if row['date_filed'] else 'N/A'
        print(f"\n• {row['case_name'][:60]}")
        print(f"  Filed: {date_str}")
        print(f"  Citations: {row['citation_count'] or 0}")
        print(f"  Content length: {row['content_length']} chars")

    await conn.close()

async def main():
    """Main import process"""
    print("""
╔══════════════════════════════════════════════╗
║      Import Real Case Data from CourtListener  ║
╚══════════════════════════════════════════════╝
    """)

    try:
        # Import cases
        count = await import_cases_from_search()

        if count > 0:
            # Show results
            await show_results()
            print("\n✅ Import successful!")
            print("\nYour database now has real case data with:")
            print("• Case names and metadata")
            print("• Full text content (where available)")
            print("• Embeddings for semantic search")
            print("\nYou can now test search functionality!")
        else:
            print("\n⚠️ No cases were imported")

    except Exception as e:
        print(f"\n❌ Import failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())