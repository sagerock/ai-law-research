#!/usr/bin/env python3

"""
Test Minimal Setup (PostgreSQL + Redis only)
Works without OpenSearch for initial testing
"""

import os
import asyncio
import asyncpg
import redis.asyncio as redis
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def test_postgres():
    """Test PostgreSQL and pgvector"""
    print("Testing PostgreSQL...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check PostgreSQL version
        version = await conn.fetchval("SELECT version()")
        print(f"✓ PostgreSQL connected: {version[:40]}...")

        # Check pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("✓ pgvector extension available")

        await conn.close()
        return True
    except Exception as e:
        print(f"✗ PostgreSQL failed: {e}")
        return False

async def test_redis():
    """Test Redis connection"""
    print("\nTesting Redis...")
    try:
        client = await redis.from_url(REDIS_URL)
        await client.ping()
        print("✓ Redis connected")
        await client.close()
        return True
    except Exception as e:
        print(f"✗ Redis failed: {e}")
        return False

async def test_openai():
    """Test OpenAI API"""
    print("\nTesting OpenAI API...")
    if not OPENAI_API_KEY:
        print("⚠ No OpenAI API key in .env file")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "input": "legal test",
                    "model": "text-embedding-3-small"
                }
            )
            if response.status_code == 200:
                data = response.json()
                embedding = data["data"][0]["embedding"]
                print(f"✓ OpenAI API working (embedding dimension: {len(embedding)})")
                return True
            else:
                print(f"✗ OpenAI API failed: {response.status_code}")
                print(f"  {response.text[:200]}")
                return False
    except Exception as e:
        print(f"✗ OpenAI API error: {e}")
        return False

async def test_courtlistener():
    """Test CourtListener API"""
    print("\nTesting CourtListener API...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.courtlistener.com/api/rest/v4/courts/",
                params={"page_size": 1}
            )
            if response.status_code == 200:
                print("✓ CourtListener API accessible")
                return True
            else:
                print(f"✗ CourtListener API failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ CourtListener error: {e}")
        return False

async def create_tables():
    """Create basic tables for testing"""
    print("\nCreating database tables...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create minimal schema
        await conn.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;

            CREATE TABLE IF NOT EXISTS test_cases (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                embedding vector(1536),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        print("✓ Tables created")
        await conn.close()
        return True
    except Exception as e:
        print(f"✗ Table creation failed: {e}")
        return False

async def test_data_flow():
    """Test complete data flow"""
    print("\nTesting data flow...")

    if not OPENAI_API_KEY:
        print("⚠ Skipping - needs OpenAI API key")
        return False

    try:
        # Generate embedding
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "input": "This is a test legal document about personal jurisdiction",
                    "model": "text-embedding-3-small"
                }
            )
            embedding = response.json()["data"][0]["embedding"]

        # Store in PostgreSQL
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            INSERT INTO test_cases (id, title, content, embedding)
            VALUES ($1, $2, $3, $4::vector)
            ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding
        """, "test-1", "Test Case", "Test content", embedding)

        # Search with similarity
        result = await conn.fetchrow("""
            SELECT id, title,
                   1 - (embedding <=> $1::vector) as similarity
            FROM test_cases
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT 1
        """, embedding)

        if result:
            print(f"✓ Data flow working - similarity: {result['similarity']:.4f}")
            await conn.close()
            return True
        else:
            print("✗ Data flow failed")
            await conn.close()
            return False

    except Exception as e:
        print(f"✗ Data flow error: {e}")
        return False

async def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════╗
║     Legal Research Tool - Minimal Test        ║
╚══════════════════════════════════════════════╝
    """)

    results = {
        "PostgreSQL": await test_postgres(),
        "Redis": await test_redis(),
        "OpenAI API": await test_openai(),
        "CourtListener": await test_courtlistener(),
        "Tables": await create_tables(),
        "Data Flow": await test_data_flow()
    }

    print("\n" + "="*50)
    print("RESULTS")
    print("="*50)

    for service, status in results.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {service}")

    # Check if ready
    core_ready = results["PostgreSQL"] and results["Redis"] and results["Tables"]

    if core_ready:
        print("\n✅ Core services ready!")
        print("\nYou can now:")

        if results["OpenAI API"]:
            print("• Import data with embeddings: python scripts/initial_import.py")
        else:
            print("• Add OpenAI API key to .env for embeddings")

        print("• Test API: python scripts/test_api.py")
        print("\nNote: OpenSearch not required for basic testing")
    else:
        print("\n⚠️ Some core services failed")
        print("Make sure PostgreSQL and Redis are running")

if __name__ == "__main__":
    asyncio.run(main())