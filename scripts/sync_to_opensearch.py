#!/usr/bin/env python3
"""
Sync cases from PostgreSQL to OpenSearch
"""

import asyncio
import asyncpg
import os
from opensearchpy import AsyncOpenSearch
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")

async def sync_to_opensearch():
    """Sync all cases from PostgreSQL to OpenSearch"""

    print("="*80)
    print("🔄 SYNCING POSTGRESQL → OPENSEARCH")
    print("="*80)

    # Connect to PostgreSQL
    print("\n📊 Connecting to PostgreSQL...")
    conn = await asyncpg.connect(DATABASE_URL)

    # Connect to OpenSearch
    print("🔍 Connecting to OpenSearch...")
    client = AsyncOpenSearch(
        hosts=[OPENSEARCH_URL],
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False
    )

    try:
        # Get all cases with court info
        print("\n📥 Fetching cases from PostgreSQL...")
        cases = await conn.fetch("""
            SELECT
                c.id,
                c.title,
                c.court_id,
                ct.name as court_name,
                c.decision_date,
                c.reporter_cite,
                c.content,
                c.metadata,
                c.source_url,
                c.created_at
            FROM cases c
            LEFT JOIN courts ct ON c.court_id = ct.id
            ORDER BY c.created_at DESC
        """)

        print(f"   Found {len(cases)} cases in PostgreSQL")

        if not cases:
            print("\n⚠️  No cases to sync")
            return

        # Index each case
        print(f"\n📤 Indexing cases to OpenSearch...")
        indexed = 0
        errors = 0

        for i, case in enumerate(cases, 1):
            try:
                doc = {
                    "title": case['title'],
                    "court_id": case['court_id'],
                    "court_name": case['court_name'],
                    "decision_date": case['decision_date'].isoformat() if case['decision_date'] else None,
                    "reporter_cite": case['reporter_cite'],
                    "content": case['content'],
                    "metadata": case['metadata'],
                    "source_url": case['source_url'],
                    "created_at": case['created_at'].isoformat() if case['created_at'] else None
                }

                await client.index(
                    index="cases",
                    id=case['id'],
                    body=doc,
                    refresh=False  # Don't refresh after each insert for speed
                )

                indexed += 1

                if i % 10 == 0:
                    print(f"   Indexed {i}/{len(cases)} cases...")

            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ❌ Error indexing case {case['id']}: {e}")

        # Refresh index to make documents searchable
        print("\n🔄 Refreshing OpenSearch index...")
        await client.indices.refresh(index="cases")

        # Verify count
        count_result = await client.count(index="cases")
        opensearch_count = count_result['count']

        print(f"\n{'='*80}")
        print("✅ SYNC COMPLETE!")
        print(f"{'='*80}")
        print(f"  PostgreSQL cases: {len(cases)}")
        print(f"  Successfully indexed: {indexed}")
        print(f"  Errors: {errors}")
        print(f"  OpenSearch total: {opensearch_count}")
        print(f"\n🎉 Your cases are now searchable in the frontend!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await conn.close()
        await client.close()

if __name__ == "__main__":
    asyncio.run(sync_to_opensearch())
