#!/usr/bin/env python3

"""
Test the search functionality with imported data
"""

import asyncio
import asyncpg
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def test_keyword_search(query: str):
    """Test PostgreSQL full-text search"""
    print(f"\n🔍 Keyword Search: '{query}'")
    print("-" * 50)

    conn = await asyncpg.connect(DATABASE_URL)

    results = await conn.fetch("""
        SELECT case_name, date_filed, citation_count, content
        FROM cases
        WHERE content ILIKE $1
        LIMIT 5
    """, f"%{query}%")

    if results:
        for row in results:
            print(f"• {row['case_name'][:60]}")
            print(f"  Filed: {row['date_filed']}, Citations: {row['citation_count'] or 0}")
            if row['content']:
                print(f"  Snippet: {row['content'][:100]}...")
    else:
        print("No results found")

    await conn.close()

async def test_semantic_search(query: str):
    """Test pgvector semantic search"""
    print(f"\n🧠 Semantic Search: '{query}'")
    print("-" * 50)

    if not OPENAI_API_KEY:
        print("⚠ Semantic search requires OpenAI API key")
        return

    # Generate embedding for query
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"input": query, "model": "text-embedding-3-small"}
        )

        if response.status_code != 200:
            print(f"Error generating embedding: {response.status_code}")
            return

        query_embedding = response.json()["data"][0]["embedding"]

    # Search using cosine similarity
    conn = await asyncpg.connect(DATABASE_URL)

    # Convert list to PostgreSQL array format
    embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

    results = await conn.fetch("""
        SELECT case_name, date_filed, citation_count,
               1 - (embedding <=> $1::vector) as similarity
        FROM cases
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT 5
    """, embedding_str)

    if results:
        print("Top semantic matches:")
        for row in results:
            print(f"• {row['case_name'][:60]}")
            print(f"  Similarity: {row['similarity']:.4f}")
            print(f"  Filed: {row['date_filed']}")
    else:
        print("No results with embeddings found")

    await conn.close()

async def show_stats():
    """Show database statistics"""
    print("\n📊 Database Statistics")
    print("-" * 50)

    conn = await asyncpg.connect(DATABASE_URL)

    case_count = await conn.fetchval("SELECT COUNT(*) FROM cases")
    embedding_count = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE embedding IS NOT NULL")
    court_count = await conn.fetchval("SELECT COUNT(*) FROM courts")
    citation_count = await conn.fetchval("SELECT COUNT(*) FROM citations")

    print(f"Total cases: {case_count}")
    print(f"Cases with embeddings: {embedding_count}")
    print(f"Courts: {court_count}")
    print(f"Citations: {citation_count}")

    # Top cited cases
    print("\nMost cited cases:")
    top_cases = await conn.fetch("""
        SELECT case_name, citation_count
        FROM cases
        WHERE citation_count > 0
        ORDER BY citation_count DESC
        LIMIT 3
    """)

    for row in top_cases:
        print(f"• {row['case_name'][:50]} ({row['citation_count']} citations)")

    await conn.close()

async def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════╗
║           Legal Search Test Suite             ║
╚══════════════════════════════════════════════╝
    """)

    # Show current data
    await show_stats()

    # Test searches
    test_queries = [
        "jurisdiction",
        "immunity",
        "summary judgment"
    ]

    for query in test_queries:
        await test_keyword_search(query)
        await test_semantic_search(query)

    print("\n✅ Search tests complete!")

if __name__ == "__main__":
    asyncio.run(main())