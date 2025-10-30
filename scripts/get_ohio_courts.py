#!/usr/bin/env python3
"""
Get Ohio court IDs from CourtListener API
"""

import asyncio
import httpx
import json

async def get_ohio_courts():
    """Fetch all Ohio courts from CourtListener"""
    print("Fetching Ohio courts from CourtListener API...\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch all courts
        response = await client.get(
            'https://www.courtlistener.com/api/rest/v4/courts/',
            params={'page_size': 500}
        )

        if response.status_code == 200:
            data = response.json()

            # Filter for Ohio courts - check multiple fields
            ohio_courts = []
            for c in data['results']:
                # Check if Ohio is in any relevant field
                if any([
                    'ohio' in str(c.get('full_name', '')).lower(),
                    'ohio' in str(c.get('short_name', '')).lower(),
                    'ohio' in str(c.get('jurisdiction', '')).lower(),
                    c.get('id', '').startswith('oh'),
                    ' oh ' in str(c.get('full_name', '')).lower(),
                ]):
                    ohio_courts.append(c)

            # Federal courts covering Ohio
            federal_courts = [
                c for c in data['results']
                if c['id'] in ['ca6', 'ohnd', 'ohsd', 'ohnd-temp-bank', 'ohsd-temp-bank']
            ]

            print("=" * 80)
            print("OHIO STATE COURTS")
            print("=" * 80)
            if ohio_courts:
                for court in sorted(ohio_courts, key=lambda x: x['id']):
                    print(f"{court['id']:25} - {court['full_name']}")
                    if court.get('jurisdiction'):
                        print(f"{'':25}   Jurisdiction: {court['jurisdiction']}")
            else:
                print("⚠️  No Ohio state courts found in CourtListener")
                print("   (Ohio state courts may not be in CourtListener's database)")

            print("\n" + "=" * 80)
            print("FEDERAL COURTS (Ohio jurisdiction)")
            print("=" * 80)
            if federal_courts:
                for court in federal_courts:
                    print(f"{court['id']:25} - {court['full_name']}")
            else:
                print("⚠️  No federal courts found for Ohio")

            print(f"\n📊 Summary:")
            print(f"   Ohio state courts: {len(ohio_courts)}")
            print(f"   Federal courts: {len(federal_courts)}")
            print(f"   Total: {len(ohio_courts) + len(federal_courts)}")

            # Check if we have federal district courts
            all_federal_ohio = [c for c in data['results'] if 'ohio' in c.get('full_name', '').lower() and c.get('id', '').startswith(('ca', 'oh'))]

            if all_federal_ohio:
                print("\n   All potential federal Ohio courts:")
                for c in all_federal_ohio:
                    print(f"      {c['id']:20} - {c['full_name']}")

            # Save to JSON for reference
            all_ohio = ohio_courts + federal_courts
            with open('/Volumes/T7/Scripts/AI Law Researcher/legal-research-tool/ohio_courts.json', 'w') as f:
                json.dump(all_ohio, f, indent=2)

            print(f"\n✅ Saved court data to ohio_courts.json")

            # Important note
            print("\n" + "=" * 80)
            print("⚠️  IMPORTANT NOTE:")
            print("=" * 80)
            print("CourtListener primarily focuses on federal courts.")
            print("Ohio state courts (Supreme Court, appellate districts) may have limited")
            print("coverage or require searching by jurisdiction rather than court ID.")
            print("\nWe can still import Ohio cases by:")
            print("  1. Searching for jurisdiction: 'Ohio' or 'OH'")
            print("  2. Using federal courts: 6th Circuit, N.D. Ohio, S.D. Ohio")
            print("  3. Filtering search results by state")

            return all_ohio
        else:
            print(f"❌ Failed to fetch courts: {response.status_code}")
            return []

if __name__ == "__main__":
    asyncio.run(get_ohio_courts())
