#!/usr/bin/env python3
"""
Test searching for Ohio cases on CourtListener to see what's available
"""

import asyncio
import httpx
import json

async def test_ohio_search():
    """Test different search strategies for Ohio cases"""
    print("Testing Ohio case searches on CourtListener...\n")

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Test 1: Search for Ohio Supreme Court cases
        print("=" * 80)
        print("TEST 1: Searching for 'Ohio Supreme Court' cases")
        print("=" * 80)

        response = await client.get(
            'https://www.courtlistener.com/api/rest/v4/search/',
            params={
                'q': 'court:"Ohio Supreme Court"',
                'type': 'o',
                'page_size': 5
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Results found: {data.get('count', 0)}")
            if data.get('results'):
                print("\nSample cases:")
                for i, case in enumerate(data['results'][:3], 1):
                    print(f"  {i}. {case.get('caseName', 'N/A')}")
                    print(f"     Court: {case.get('court', 'N/A')}")
                    print(f"     Court ID: {case.get('court_id', 'N/A')}")
                    print(f"     Date: {case.get('dateFiled', 'N/A')}")
        else:
            print(f"❌ Search failed: {response.status_code}")

        # Test 2: Search with jurisdiction filter
        print("\n" + "=" * 80)
        print("TEST 2: Searching with jurisdiction filter")
        print("=" * 80)

        response = await client.get(
            'https://www.courtlistener.com/api/rest/v4/search/',
            params={
                'q': 'jurisdiction:Ohio',
                'type': 'o',
                'page_size': 5
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Results found: {data.get('count', 0)}")
            if data.get('results'):
                print("\nSample cases:")
                for i, case in enumerate(data['results'][:3], 1):
                    print(f"  {i}. {case.get('caseName', 'N/A')}")
                    print(f"     Court: {case.get('court', 'N/A')}")
                    print(f"     Court ID: {case.get('court_id', 'N/A')}")
        else:
            print(f"❌ Search failed: {response.status_code}")

        # Test 3: Search 6th Circuit (covers Ohio)
        print("\n" + "=" * 80)
        print("TEST 3: Searching 6th Circuit (covers Ohio)")
        print("=" * 80)

        response = await client.get(
            'https://www.courtlistener.com/api/rest/v4/search/',
            params={
                'q': 'court_id:ca6',
                'type': 'o',
                'page_size': 5,
                'order_by': 'dateFiled desc'
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Results found: {data.get('count', 0)}")
            if data.get('results'):
                print("\nSample cases:")
                for i, case in enumerate(data['results'][:3], 1):
                    print(f"  {i}. {case.get('caseName', 'N/A')}")
                    print(f"     Court: {case.get('court', 'N/A')}")
                    print(f"     Date: {case.get('dateFiled', 'N/A')}")
        else:
            print(f"❌ Search failed: {response.status_code}")

        # Test 4: Just search for "Ohio" in case text
        print("\n" + "=" * 80)
        print("TEST 4: Broad search for Ohio-related cases")
        print("=" * 80)

        response = await client.get(
            'https://www.courtlistener.com/api/rest/v4/search/',
            params={
                'q': 'Ohio',
                'type': 'o',
                'page_size': 10
            }
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Results found: {data.get('count', 0)}")

            # Count unique courts
            courts = {}
            for case in data.get('results', []):
                court_id = case.get('court_id', 'unknown')
                court_name = case.get('court', 'Unknown')
                if court_id not in courts:
                    courts[court_id] = {'name': court_name, 'count': 0}
                courts[court_id]['count'] += 1

            print("\nCourts found:")
            for court_id, info in sorted(courts.items(), key=lambda x: x[1]['count'], reverse=True):
                print(f"  {court_id:15} - {info['name']:50} ({info['count']} cases)")
        else:
            print(f"❌ Search failed: {response.status_code}")

        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("=" * 80)
        print("Based on these tests, we can identify which search strategy will work best")
        print("for importing Ohio cases into your legal research tool.")

if __name__ == "__main__":
    asyncio.run(test_ohio_search())
