#!/usr/bin/env python3
"""
Set up production PostgreSQL database and migrate data from local
"""

import asyncio
import asyncpg
import os
import json

# Local database
LOCAL_DATABASE_URL = "postgresql://legal_user:legal_pass@localhost:5432/legal_research"

# Production database - get from Railway environment variable
PROD_DATABASE_URL = os.environ.get("DATABASE_URL")

if not PROD_DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    print("   Please set it to your Railway PostgreSQL connection string:")
    print("   export DATABASE_URL='postgresql://...'")
    exit(1)

async def setup_production_database():
    """Initialize production database and migrate data"""

    print("="*80)
    print("🔄 SETTING UP PRODUCTION DATABASE")
    print("="*80)

    # Connect to production PostgreSQL
    print("\n📊 Connecting to production PostgreSQL...")
    prod_conn = await asyncpg.connect(PROD_DATABASE_URL)

    try:
        # Read and execute schema migration (without pgvector for Railway compatibility)
        print("\n📋 Creating database schema...")
        with open('/Volumes/T7/Scripts/AI Law Researcher/legal-research-tool/migrations/001_init_no_vector.sql', 'r') as f:
            schema_sql = f.read()

        await prod_conn.execute(schema_sql)
        print("   ✅ Schema created successfully (without pgvector - semantic search will use OpenSearch)")

        # Connect to local database
        print("\n📥 Connecting to local PostgreSQL...")
        local_conn = await asyncpg.connect(LOCAL_DATABASE_URL)

        try:
            # Get all courts from local database
            print("\n📤 Migrating courts...")
            courts = await local_conn.fetch("SELECT * FROM courts")

            for court in courts:
                await prod_conn.execute("""
                    INSERT INTO courts (id, name, jurisdiction, level, abbreviation, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        jurisdiction = EXCLUDED.jurisdiction,
                        level = EXCLUDED.level,
                        abbreviation = EXCLUDED.abbreviation
                """, court['id'], court['name'], court.get('jurisdiction'),
                     court.get('level'), court.get('abbreviation'), court.get('created_at'))

            print(f"   ✅ Migrated {len(courts)} courts")

            # Get all cases from local database
            print("\n📤 Migrating cases...")
            cases = await local_conn.fetch("""
                SELECT * FROM cases ORDER BY created_at DESC
            """)

            migrated = 0
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

                    await prod_conn.execute("""
                        INSERT INTO cases (
                            id, court_id, title, docket_number, decision_date,
                            reporter_cite, neutral_cite, precedential, content,
                            content_hash, metadata, source_url,
                            created_at, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        ON CONFLICT (id) DO UPDATE
                        SET title = EXCLUDED.title,
                            court_id = EXCLUDED.court_id,
                            decision_date = EXCLUDED.decision_date,
                            reporter_cite = EXCLUDED.reporter_cite,
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                    """,
                        case['id'],
                        case['court_id'],
                        case['title'],
                        case.get('docket_number'),
                        case.get('decision_date'),
                        case.get('reporter_cite'),
                        case.get('neutral_cite'),
                        case.get('precedential', True),
                        case.get('content'),
                        case.get('content_hash'),
                        json.dumps(metadata) if metadata else None,
                        case.get('source_url'),
                        case.get('created_at'),
                        case.get('updated_at')
                    )

                    migrated += 1

                    if i % 10 == 0:
                        print(f"   Migrated {i}/{len(cases)} cases...")

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"   ❌ Error migrating case {case.get('id')}: {e}")

            print(f"\n{'='*80}")
            print("✅ MIGRATION COMPLETE!")
            print(f"{'='*80}")
            print(f"  Courts migrated: {len(courts)}")
            print(f"  Cases migrated: {migrated}")
            print(f"  Errors: {errors}")

            # Verify counts
            prod_case_count = await prod_conn.fetchval("SELECT COUNT(*) FROM cases")
            prod_court_count = await prod_conn.fetchval("SELECT COUNT(*) FROM courts")

            print(f"\n📊 Production Database Status:")
            print(f"  Total courts: {prod_court_count}")
            print(f"  Total cases: {prod_case_count}")
            print(f"\n🎉 Your production database is ready!")

        finally:
            await local_conn.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await prod_conn.close()

if __name__ == "__main__":
    asyncio.run(setup_production_database())
