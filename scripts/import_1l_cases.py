#!/usr/bin/env python3
"""
Import 1L Core Cases from CourtListener API into PostgreSQL.

Reads case IDs from the local SQLite database (matched from Quimbee),
fetches full case data and opinion text from CourtListener API,
and imports into the PostgreSQL database.

Usage:
    python scripts/import_1l_cases.py
    python scripts/import_1l_cases.py --limit 10  # Test with 10 cases
    python scripts/import_1l_cases.py --dry-run   # Show what would be imported
"""

import argparse
import asyncio
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from html import unescape

import asyncpg
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")
SQLITE_DB = Path("data/courtlistener/citations.db")

# API settings
API_BASE = "https://www.courtlistener.com/api/rest/v4"
RATE_LIMIT_DELAY = 0.5  # seconds between requests


def html_to_text(html: str) -> str:
    """Convert HTML to plain text, preserving paragraph structure."""
    if not html:
        return ""
    soup = BeautifulSoup(html, 'html.parser')

    # Remove script and style elements
    for element in soup(['script', 'style']):
        element.decompose()

    # Get text with newlines for block elements
    text = soup.get_text(separator='\n', strip=True)

    # Clean up excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = unescape(text)

    return text


async def fetch_cluster(client: httpx.AsyncClient, cluster_id: str) -> Optional[dict]:
    """Fetch cluster (case) metadata from CourtListener API."""
    try:
        response = await client.get(
            f"{API_BASE}/clusters/{cluster_id}/",
            headers={"Authorization": f"Token {COURTLISTENER_API_KEY}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ⚠ Failed to fetch cluster {cluster_id}: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"  ⚠ Error fetching cluster {cluster_id}: {e}")
        return None


async def fetch_opinion(client: httpx.AsyncClient, opinion_url: str) -> Optional[dict]:
    """Fetch opinion text from CourtListener API."""
    try:
        response = await client.get(
            opinion_url,
            headers={"Authorization": f"Token {COURTLISTENER_API_KEY}"}
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"  ⚠ Error fetching opinion: {e}")
        return None


async def get_opinion_text(client: httpx.AsyncClient, cluster_data: dict) -> str:
    """Get the full opinion text from a cluster's sub_opinions."""
    texts = []

    for opinion_url in cluster_data.get("sub_opinions", []):
        opinion_data = await fetch_opinion(client, opinion_url)
        if opinion_data:
            # Try different HTML fields in order of preference
            html = (
                opinion_data.get("html_columbia") or
                opinion_data.get("html_lawbox") or
                opinion_data.get("html") or
                opinion_data.get("html_with_citations") or
                opinion_data.get("html_anon_2020") or
                ""
            )
            if html:
                text = html_to_text(html)
                if text:
                    # Add author info if available
                    author = opinion_data.get("author_str", "")
                    opinion_type = opinion_data.get("type", "")
                    if author and opinion_type == "020lead":
                        texts.append(f"Opinion by {author}:\n\n{text}")
                    elif author and opinion_type == "040dissent":
                        texts.append(f"Dissent by {author}:\n\n{text}")
                    elif author and opinion_type == "030concurrence":
                        texts.append(f"Concurrence by {author}:\n\n{text}")
                    else:
                        texts.append(text)

            # Also try plain_text if no HTML
            if not html and opinion_data.get("plain_text"):
                texts.append(opinion_data["plain_text"])

        await asyncio.sleep(RATE_LIMIT_DELAY)

    return "\n\n---\n\n".join(texts)


def format_citation(citations: list) -> Optional[str]:
    """Format the primary citation from a list of citation objects."""
    if not citations:
        return None

    # Prefer official reporters (type 2) or regional reporters (type 3)
    for citation in citations:
        if citation.get("type") in [2, 3]:
            volume = citation.get("volume", "")
            reporter = citation.get("reporter", "")
            page = citation.get("page", "")
            if volume and reporter and page:
                return f"{volume} {reporter} {page}"

    # Fall back to first available
    for citation in citations:
        volume = citation.get("volume", "")
        reporter = citation.get("reporter", "")
        page = citation.get("page", "")
        if volume and reporter and page:
            return f"{volume} {reporter} {page}"

    return None


async def import_cases(limit: Optional[int] = None, dry_run: bool = False):
    """Import 1L core cases from CourtListener into PostgreSQL."""

    print("=" * 70)
    print("1L CORE CASES IMPORTER")
    print("=" * 70)

    # Check API key
    if not COURTLISTENER_API_KEY:
        print("\n❌ Error: COURTLISTENER_API_KEY not set in environment")
        return 1

    # Connect to SQLite to get case list
    if not SQLITE_DB.exists():
        print(f"\n❌ Error: SQLite database not found at {SQLITE_DB}")
        return 1

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    cursor = sqlite_conn.cursor()

    # Get cases with CourtListener IDs
    cursor.execute("""
        SELECT lsc.case_name, lsc.courtlistener_id, lsc.citation, lsc.date_filed,
               ls.name as subject
        FROM law_school_cases lsc
        JOIN law_subjects ls ON lsc.subject_id = ls.id
        WHERE lsc.courtlistener_id IS NOT NULL AND lsc.courtlistener_id != ''
        ORDER BY lsc.casebook_count DESC
    """)
    cases = cursor.fetchall()
    sqlite_conn.close()

    if limit:
        cases = cases[:limit]

    print(f"\n📋 Found {len(cases)} cases to import")

    if dry_run:
        print("\n[DRY RUN - No changes will be made]")
        for case_name, cl_id, citation, date_filed, subject in cases[:20]:
            print(f"  • {case_name} ({citation or 'no citation'}) - {subject}")
        if len(cases) > 20:
            print(f"  ... and {len(cases) - 20} more")
        return 0

    # Connect to PostgreSQL
    try:
        pg_conn = await asyncpg.connect(DATABASE_URL)
        print(f"\n✓ Connected to PostgreSQL")
    except Exception as e:
        print(f"\n❌ Failed to connect to PostgreSQL: {e}")
        return 1

    # Track statistics
    stats = {
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "no_text": 0
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for idx, (case_name, cl_id, citation, date_filed, subject) in enumerate(cases, 1):
            print(f"\n[{idx}/{len(cases)}] {case_name[:60]}")
            print(f"  CourtListener ID: {cl_id}")

            # Check if already exists
            existing = await pg_conn.fetchrow(
                "SELECT id FROM cases WHERE id = $1", cl_id
            )
            if existing:
                print(f"  ⏭ Already exists, skipping")
                stats["skipped"] += 1
                continue

            # Fetch cluster metadata
            cluster = await fetch_cluster(client, cl_id)
            if not cluster:
                stats["failed"] += 1
                continue

            await asyncio.sleep(RATE_LIMIT_DELAY)

            # Fetch opinion text
            print(f"  📥 Fetching opinion text...")
            opinion_text = await get_opinion_text(client, cluster)

            if not opinion_text:
                print(f"  ⚠ No opinion text found")
                stats["no_text"] += 1
                # Still import with metadata only

            # Get or create court
            court_name = "Unknown Court"
            if cluster.get("docket"):
                # Would need another API call to get court name
                # For now, we'll extract from case name or use default
                pass

            court_id = await pg_conn.fetchval(
                """
                INSERT INTO courts (name, jurisdiction, level)
                VALUES ($1, 'federal', 'appellate')
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                court_name
            )

            # Format citation
            primary_citation = format_citation(cluster.get("citations", []))
            if not primary_citation and citation:
                primary_citation = citation

            # Parse date
            filed_date = None
            date_str = cluster.get("date_filed") or date_filed
            if date_str:
                try:
                    filed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except:
                    pass

            # Build metadata
            metadata = {
                "subject": subject,
                "judges": cluster.get("judges"),
                "citation_count": cluster.get("citation_count", 0),
                "precedential_status": cluster.get("precedential_status"),
                "source": "courtlistener_api",
                "import_date": datetime.now().isoformat()
            }

            # Insert case
            try:
                await pg_conn.execute(
                    """
                    INSERT INTO cases (
                        id, court_id, title, decision_date, reporter_cite,
                        content, metadata, source_url, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                    """,
                    cl_id,
                    court_id,
                    cluster.get("case_name") or case_name,
                    filed_date,
                    primary_citation,
                    opinion_text or "",
                    json.dumps(metadata),
                    f"https://www.courtlistener.com{cluster.get('absolute_url', '')}"
                )

                text_len = len(opinion_text) if opinion_text else 0
                print(f"  ✓ Imported ({text_len:,} chars)")
                stats["imported"] += 1

            except Exception as e:
                print(f"  ❌ Failed to insert: {e}")
                stats["failed"] += 1

    await pg_conn.close()

    # Summary
    print(f"\n{'=' * 70}")
    print("IMPORT COMPLETE")
    print(f"{'=' * 70}")
    print(f"  ✓ Imported: {stats['imported']}")
    print(f"  ⏭ Skipped (existing): {stats['skipped']}")
    print(f"  ⚠ No text found: {stats['no_text']}")
    print(f"  ❌ Failed: {stats['failed']}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Import 1L core cases from CourtListener")
    parser.add_argument("--limit", type=int, help="Limit number of cases to import")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported")
    args = parser.parse_args()

    return asyncio.run(import_cases(limit=args.limit, dry_run=args.dry_run))


if __name__ == "__main__":
    exit(main())
