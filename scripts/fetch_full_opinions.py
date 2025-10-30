#!/usr/bin/env python3

"""
Fetch full opinion text from CourtListener HTML pages
and update the database
"""

import asyncio
import asyncpg
import httpx
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import time

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")

async def fetch_opinion_text(source_url: str) -> str:
    """Scrape full opinion text from CourtListener HTML page"""
    if not source_url:
        return ""

    full_url = f"https://www.courtlistener.com{source_url}" if source_url.startswith('/') else source_url

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(full_url, follow_redirects=True)

            if response.status_code != 200:
                print(f"  ⚠ Failed to fetch {full_url}: HTTP {response.status_code}")
                return ""

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the opinion text - CourtListener uses specific classes
            opinion_body = soup.find('div', class_='opinion-body')
            if not opinion_body:
                # Try alternative selectors
                opinion_body = soup.find('article', class_='col-sm-9')
                if not opinion_body:
                    opinion_body = soup.find('div', id='opinion-content')

            if opinion_body:
                # Extract text, preserving some structure
                text = opinion_body.get_text(separator='\n', strip=True)
                return text
            else:
                print(f"  ⚠ Could not find opinion text in {full_url}")
                return ""

    except Exception as e:
        print(f"  ⚠ Error fetching {full_url}: {e}")
        return ""

async def update_case_content(case_id: str, content: str, conn):
    """Update case content in database"""
    await conn.execute(
        "UPDATE cases SET content = $1, updated_at = NOW() WHERE id = $2",
        content, case_id
    )

async def process_cases():
    """Fetch full text for all cases with short or missing content"""
    print("\n🔍 Fetching full opinion text from CourtListener...")

    conn = await asyncpg.connect(DATABASE_URL)

    # Find cases with short or missing content
    cases = await conn.fetch("""
        SELECT id, title, source_url, LENGTH(content) as content_len
        FROM cases
        WHERE source_url IS NOT NULL
          AND (content IS NULL OR LENGTH(content) < 500)
        ORDER BY created_at DESC
        LIMIT 20
    """)

    print(f"\n📋 Found {len(cases)} cases needing full text\n")

    success_count = 0

    for idx, case in enumerate(cases, 1):
        print(f"[{idx}/{len(cases)}] {case['title'][:60]}...")
        print(f"  URL: {case['source_url']}")
        print(f"  Current length: {case['content_len']} chars")

        # Fetch full text
        full_text = await fetch_opinion_text(case['source_url'])

        if full_text and len(full_text) > 500:
            await update_case_content(case['id'], full_text, conn)
            print(f"  ✓ Updated with {len(full_text)} chars")
            success_count += 1
        else:
            print(f"  ⚠ No content fetched or too short")

        # Be polite - don't hammer the server
        await asyncio.sleep(2)

    await conn.close()

    print(f"\n{'='*60}")
    print(f"✅ Successfully updated {success_count}/{len(cases)} cases")
    print(f"{'='*60}\n")

async def main():
    """Run the opinion fetcher"""
    print("""
╔══════════════════════════════════════════════════════╗
║   Fetch Full Opinion Text from CourtListener         ║
╚══════════════════════════════════════════════════════╝
    """)

    try:
        await process_cases()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
