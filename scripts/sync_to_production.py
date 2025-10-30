#!/usr/bin/env python3
"""
Sync local cases to production OpenSearch
"""

import asyncio
import asyncpg
import os
import json
from opensearchpy import AsyncOpenSearch

# Local database
LOCAL_DATABASE_URL = "postgresql://legal_user:legal_pass@localhost:5432/legal_research"

# Production OpenSearch
PROD_OPENSEARCH_URL = "https://2a01db3e3f:bb4b793dbb9748db1a82@law-researcher-1hx7y39w.us-east-1.bonsaisearch.net"

async def sync_to_production():
    """Sync all cases from local PostgreSQL to production OpenSearch"""

    print("="*80)
    print("🔄 SYNCING LOCAL → PRODUCTION OPENSEARCH")
    print("="*80)

    # Connect to local PostgreSQL
    print("\n📊 Connecting to local PostgreSQL...")
    local_conn = await asyncpg.connect(LOCAL_DATABASE_URL)

    # Connect to production OpenSearch
    print("🔍 Connecting to production OpenSearch...")
    prod_client = AsyncOpenSearch(
        hosts=[PROD_OPENSEARCH_URL],
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False
    )

    try:
        # Get all cases from local database
        print("\n📥 Fetching cases from local PostgreSQL...")
        cases = await local_conn.fetch("""
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

        print(f"   Found {len(cases)} cases in local database")

        if not cases:
            print("\n⚠️  No cases to sync")
            return

        # Index each case to production
        print(f"\n📤 Indexing cases to production OpenSearch...")
        indexed = 0
        errors = 0

        for i, case in enumerate(cases, 1):
            try:
                # Parse metadata if it's a JSON string
                metadata = case['metadata']
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                elif metadata is None:
                    metadata = {}

                doc = {
                    "title": case['title'],
                    "court_id": case['court_id'],
                    "court_name": case['court_name'],
                    "decision_date": case['decision_date'].isoformat() if case['decision_date'] else None,
                    "reporter_cite": case['reporter_cite'],
                    "content": case['content'],
                    "metadata": metadata,
                    "source_url": case['source_url'],
                    "created_at": case['created_at'].isoformat() if case['created_at'] else None
                }

                await prod_client.index(
                    index="cases",
                    id=case['id'],
                    body=doc,
                    refresh=False
                )

                indexed += 1

                if i % 10 == 0:
                    print(f"   Indexed {i}/{len(cases)} cases...")

            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ❌ Error indexing case {case['id']}: {e}")

        # Refresh index
        print("\n🔄 Refreshing OpenSearch index...")
        await prod_client.indices.refresh(index="cases")

        # Verify count
        count_result = await prod_client.count(index="cases")
        prod_count = count_result['count']

        print(f"\n{'='*80}")
        print("✅ SYNC COMPLETE!")
        print(f"{'='*80}")
        print(f"  Local cases: {len(cases)}")
        print(f"  Successfully indexed: {indexed}")
        print(f"  Errors: {errors}")
        print(f"  Production OpenSearch total: {prod_count}")
        print(f"\n🎉 Your cases are now live in production!")
        print(f"\n🌐 Visit: https://ai-law-research-production.up.railway.app")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await local_conn.close()
        await prod_client.close()

if __name__ == "__main__":
    asyncio.run(sync_to_production())
