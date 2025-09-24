#!/usr/bin/env python3

"""
Test Complete Setup
Verifies all services and API keys are working
"""

import os
import asyncio
import httpx
import asyncpg
from opensearchpy import AsyncOpenSearch
import redis.asyncio as redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")

async def test_postgres():
    """Test PostgreSQL connection"""
    print("Testing PostgreSQL...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        print(f"✓ PostgreSQL connected: {version[:30]}...")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL failed: {e}")
        return False

async def test_opensearch():
    """Test OpenSearch connection"""
    print("\nTesting OpenSearch...")
    try:
        client = AsyncOpenSearch(hosts=[OPENSEARCH_URL])
        info = await client.info()
        await client.close()
        print(f"✓ OpenSearch connected: v{info['version']['number']}")
        return True
    except Exception as e:
        print(f"✗ OpenSearch failed: {e}")
        print("  Make sure OpenSearch is running: docker-compose up -d opensearch")
        return False

async def test_redis():
    """Test Redis connection"""
    print("\nTesting Redis...")
    try:
        client = await redis.from_url(REDIS_URL)
        await client.ping()
        await client.close()
        print("✓ Redis connected")
        return True
    except Exception as e:
        print(f"✗ Redis failed: {e}")
        return False

async def test_openai():
    """Test OpenAI API"""
    print("\nTesting OpenAI API...")
    if not OPENAI_API_KEY:
        print("⚠ No OpenAI API key found")
        print("  Add OPENAI_API_KEY to your .env file")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "input": "test",
                    "model": "text-embedding-3-small"
                }
            )
            if response.status_code == 200:
                print(f"✓ OpenAI API working")
                return True
            else:
                print(f"✗ OpenAI API failed: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
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
                data = response.json()
                print(f"✓ CourtListener API working ({data['count']} courts available)")
                if not COURTLISTENER_API_KEY:
                    print("  Note: Using anonymous access (5,000 requests/day)")
                return True
            else:
                print(f"✗ CourtListener API failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ CourtListener API error: {e}")
        return False

async def main():
    """Run all tests"""
    print("""
╔══════════════════════════════════════════════╗
║        Legal Research Tool Setup Test         ║
╚══════════════════════════════════════════════╝
    """)

    results = {
        "PostgreSQL": await test_postgres(),
        "OpenSearch": await test_opensearch(),
        "Redis": await test_redis(),
        "OpenAI API": await test_openai(),
        "CourtListener": await test_courtlistener()
    }

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)

    all_pass = True
    for service, status in results.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {service}: {'Working' if status else 'Failed'}")
        if not status:
            all_pass = False

    if all_pass:
        print("\n🎉 All services are working!")
        print("\nYou can now:")
        print("1. Import data: make import-bulk")
        print("2. Or fetch via API: make etl")
        print("3. Access the API at: http://localhost:8000/docs")
    else:
        print("\n⚠️ Some services are not working")
        print("\nTroubleshooting:")
        print("1. Make sure Docker is running")
        print("2. Run: make dev")
        print("3. Check your .env file has all required keys")

if __name__ == "__main__":
    asyncio.run(main())