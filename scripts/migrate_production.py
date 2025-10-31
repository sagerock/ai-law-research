#!/usr/bin/env python3
"""
Run database migration on production PostgreSQL
"""
import os
import asyncpg
import asyncio

# Get production database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    print("   Please set it to your Railway PostgreSQL URL:")
    print("   export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
    exit(1)

async def run_migration():
    """Run the ai_summaries table migration"""

    print("="*80)
    print("🔄 RUNNING PRODUCTION DATABASE MIGRATION")
    print("="*80)
    print()

    # Connect to production database
    print("📊 Connecting to production PostgreSQL...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Check if table already exists
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'ai_summaries'
            )
            """
        )

        if exists:
            print("⚠️  Table 'ai_summaries' already exists, skipping creation")
        else:
            print("📝 Creating ai_summaries table...")

            # Create the table
            await conn.execute("""
                CREATE TABLE ai_summaries (
                    id SERIAL PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                    summary TEXT NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost DECIMAL(10, 6),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(case_id)
                )
            """)

            print("✅ Table created successfully")

            # Create index
            print("📇 Creating index...")
            await conn.execute("""
                CREATE INDEX idx_ai_summaries_case_id ON ai_summaries(case_id)
            """)

            print("✅ Index created successfully")

        # Verify
        print()
        print("🔍 Verifying table exists...")
        count = await conn.fetchval("SELECT COUNT(*) FROM ai_summaries")

        print()
        print("="*80)
        print("✅ MIGRATION COMPLETE!")
        print("="*80)
        print(f"  Cached summaries in database: {count}")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
