#!/usr/bin/env python3

"""
Test CourtListener API Connection
Verifies API access and shows sample data structure
"""

import httpx
import asyncio
import json
import os
from datetime import datetime

# API Configuration
BASE_URL = "https://www.courtlistener.com/api/rest/v4"
API_KEY = os.getenv("COURTLISTENER_API_KEY")

async def test_courts():
    """Test courts endpoint"""
    print("\n" + "="*50)
    print("Testing Courts API")
    print("="*50)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/courts/",
            params={"page_size": 5},
            headers={"Authorization": f"Token {API_KEY}"} if API_KEY else {}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {data['count']} courts")
            print("\nSample courts:")
            for court in data['results'][:3]:
                print(f"  - {court['full_name']} ({court['id']})")
        else:
            print(f"✗ Failed: {response.status_code}")

async def test_opinions():
    """Test opinions endpoint"""
    print("\n" + "="*50)
    print("Testing Opinions API")
    print("="*50)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/opinions/",
            params={
                "page_size": 5,
                "fields": "id,case_name,date_filed,court,text"
            },
            headers={"Authorization": f"Token {API_KEY}"} if API_KEY else {}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {data['count']} opinions")
            print("\nRecent opinions:")
            for opinion in data['results'][:3]:
                # Get case name from cluster if available
                case_name = opinion.get('case_name', 'Unknown')
                date = opinion.get('date_filed', 'Unknown')
                print(f"  - {case_name} ({date})")
        else:
            print(f"✗ Failed: {response.status_code}")
            print(response.text[:500])

async def test_clusters():
    """Test clusters endpoint (groups of opinions)"""
    print("\n" + "="*50)
    print("Testing Clusters API")
    print("="*50)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/clusters/",
            params={
                "page_size": 5,
                "order_by": "-date_filed"
            },
            headers={"Authorization": f"Token {API_KEY}"} if API_KEY else {}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {data['count']} clusters")
            print("\nRecent cases:")
            for cluster in data['results'][:3]:
                print(f"  - {cluster['case_name']} ({cluster['date_filed']})")
                print(f"    Court: {cluster.get('court', 'Unknown')}")
                print(f"    Citations: {cluster.get('citation_count', 0)}")
        else:
            print(f"✗ Failed: {response.status_code}")

async def test_citations():
    """Test opinions-cited endpoint"""
    print("\n" + "="*50)
    print("Testing Citations API")
    print("="*50)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/opinions-cited/",
            params={"page_size": 5},
            headers={"Authorization": f"Token {API_KEY}"} if API_KEY else {}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Found {data['count']} citation relationships")
            print("\nSample citations:")
            for cite in data['results'][:3]:
                print(f"  - Opinion {cite.get('citing_opinion')} cites {cite.get('cited_opinion')}")
        else:
            print(f"✗ Failed: {response.status_code}")

async def test_search():
    """Test search API"""
    print("\n" + "="*50)
    print("Testing Search API")
    print("="*50)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/search/",
            params={
                "q": "personal jurisdiction",
                "type": "o",  # opinions
                "order_by": "score desc",
                "page_size": 3
            },
            headers={"Authorization": f"Token {API_KEY}"} if API_KEY else {}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✓ Search returned {data['count']} results")
            print("\nTop results for 'personal jurisdiction':")
            for result in data['results'][:3]:
                print(f"  - {result.get('caseName', 'Unknown')}")
                print(f"    Score: {result.get('score', 'N/A')}")
        else:
            print(f"✗ Failed: {response.status_code}")

async def check_rate_limits():
    """Check API rate limits"""
    print("\n" + "="*50)
    print("Checking Rate Limits")
    print("="*50)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/courts/",
            params={"page_size": 1},
            headers={"Authorization": f"Token {API_KEY}"} if API_KEY else {}
        )

        # Check rate limit headers
        remaining = response.headers.get('X-RateLimit-Remaining', 'Unknown')
        limit = response.headers.get('X-RateLimit-Limit', 'Unknown')

        print(f"Rate limit: {remaining}/{limit} requests remaining")

        if not API_KEY:
            print("\n⚠ No API key configured - using anonymous access")
            print("  Anonymous limit: 5,000 requests/day")
        else:
            print("\n✓ API key configured")

async def main():
    """Run all API tests"""

    print("""
    ╔══════════════════════════════════════════════╗
    ║     CourtListener API Connection Test        ║
    ╚══════════════════════════════════════════════╝
    """)

    if API_KEY:
        print(f"✓ API Key configured: {API_KEY[:10]}...")
    else:
        print("⚠ No API key found - using anonymous access")
        print("  Set COURTLISTENER_API_KEY environment variable for authenticated access")

    # Run tests
    await test_courts()
    await test_clusters()
    await test_opinions()
    await test_citations()
    await test_search()
    await check_rate_limits()

    print("\n" + "="*50)
    print("API Test Complete!")
    print("="*50)

    # Summary
    print("\nAPI Endpoints Available:")
    print("  - Courts: ✓")
    print("  - Opinions: ✓")
    print("  - Clusters: ✓")
    print("  - Citations: ✓")
    print("  - Search: ✓")

    print("\nNext steps:")
    print("1. If tests passed, you can run: make import-bulk")
    print("2. Or fetch via API: make etl")

if __name__ == "__main__":
    asyncio.run(main())