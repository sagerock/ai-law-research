#!/usr/bin/env python3
"""
Import matched Quimbee cases into production PostgreSQL.

Reads the matched_cases.json output from match_quimbee_cases.py, creates casebook
records, imports case stubs, and optionally fetches opinion text from CourtListener.

Usage:
    python scripts/import_quimbee_cases.py                           # Import all matched
    python scripts/import_quimbee_cases.py --limit 100               # Import first 100
    python scripts/import_quimbee_cases.py --min-casebooks 5         # Only cases in 5+ textbooks
    python scripts/import_quimbee_cases.py --dry-run                 # Preview without importing
    python scripts/import_quimbee_cases.py --skip-opinions           # Import stubs only
    python scripts/import_quimbee_cases.py --fetch-text              # Fetch text for existing stubs
    python scripts/import_quimbee_cases.py --casebooks-only          # Only create casebook records
"""

import asyncio
import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import asyncpg
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
COURTLISTENER_TOKEN = os.getenv("COURTLISTENER_API_KEY") or os.getenv("COURTLISTENER_TOKEN")
LOCAL_DB_PATH = Path("data/courtlistener/citations.db")
MATCHED_FILE = Path("data/quimbee/matched_cases.json")


async def fetch_opinion_text(client: httpx.AsyncClient, cluster_id: str) -> str:
    """Fetch opinion text via CourtListener API."""
    headers = {}
    if COURTLISTENER_TOKEN:
        headers["Authorization"] = f"Token {COURTLISTENER_TOKEN}"

    try:
        response = await client.get(
            f"https://www.courtlistener.com/api/rest/v4/opinions/{cluster_id}/",
            headers=headers,
            timeout=30.0
        )

        if response.status_code == 429:
            print("  Rate limited, waiting 60s...")
            await asyncio.sleep(60)
            response = await client.get(
                f"https://www.courtlistener.com/api/rest/v4/opinions/{cluster_id}/",
                headers=headers,
                timeout=30.0
            )

        if response.status_code != 200:
            return ""

        opinion = response.json()

        if opinion.get("plain_text"):
            return opinion["plain_text"]

        for field in ["html_lawbox", "html", "html_columbia", "html_with_citations", "xml_harvard"]:
            html_content = opinion.get(field, "")
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)
                if len(text) > 100:
                    return text

    except Exception as e:
        print(f"  Error fetching opinion text: {e}")

    return ""


def get_case_metadata_from_sqlite(cluster_id: str) -> dict | None:
    """Get case metadata from local SQLite instead of API call."""
    if not LOCAL_DB_PATH.exists():
        return None

    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.case_name, c.case_name_full, c.date_filed
        FROM clusters c WHERE c.id = ?
    """, (int(cluster_id),))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    cluster_id_db, case_name, case_name_full, date_filed = row

    # Get citations
    cursor.execute("""
        SELECT volume, reporter, page FROM citations WHERE cluster_id = ? LIMIT 5
    """, (int(cluster_id),))
    cite_rows = cursor.fetchall()
    reporter_cite = f"{cite_rows[0][0]} {cite_rows[0][1]} {cite_rows[0][2]}" if cite_rows else None

    conn.close()

    return {
        "id": str(cluster_id_db),
        "title": case_name or case_name_full or "Unknown",
        "decision_date": date_filed,
        "reporter_cite": reporter_cite,
        "source_url": f"https://www.courtlistener.com/opinion/{cluster_id}/",
    }


async def create_casebooks(conn, casebooks: list[dict]) -> dict:
    """Create casebook records and return mapping of slug -> casebook_id."""
    slug_to_id = {}

    for cb in casebooks:
        try:
            casebook_id = await conn.fetchval("""
                INSERT INTO casebooks (title, subject, isbn, edition)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (title) DO UPDATE SET
                    subject = EXCLUDED.subject,
                    isbn = COALESCE(EXCLUDED.isbn, casebooks.isbn),
                    edition = COALESCE(EXCLUDED.edition, casebooks.edition),
                    updated_at = NOW()
                RETURNING id
            """, cb["title"], cb["subject"], cb.get("isbn"), cb.get("edition"))

            slug_to_id[f"{cb['subject']}/{cb['slug']}"] = casebook_id
        except Exception as e:
            print(f"  Error creating casebook '{cb['title'][:50]}': {e}")

    return slug_to_id


async def import_cases(
    input_file: Path,
    limit: int = None,
    min_casebooks: int = 1,
    dry_run: bool = False,
    skip_opinions: bool = False,
    fetch_text: bool = False,
    casebooks_only: bool = False,
    min_confidence: str = "likely"
):
    """Import matched Quimbee cases into production database."""

    if not DATABASE_URL:
        print("ERROR: Set PROD_DATABASE_URL or DATABASE_URL")
        return

    if not input_file.exists():
        print(f"ERROR: {input_file} not found")
        print("Run: python scripts/match_quimbee_cases.py")
        return

    # Load matched data
    print(f"Loading: {input_file}")
    with open(input_file) as f:
        data = json.load(f)

    stats = data.get("stats", {})
    all_cases = data.get("cases", [])
    casebooks = data.get("casebooks", [])

    print(f"Total cases: {stats.get('total', len(all_cases))}")
    print(f"Matched: {stats.get('matched', 0)}")
    print(f"Casebooks: {len(casebooks)}")

    # Filter to matched cases meeting confidence threshold
    confidence_levels = {"exact", "likely"} if min_confidence == "likely" else {"exact"}
    cases = [
        c for c in all_cases
        if c.get("cluster_id")
        and c.get("match_confidence") in confidence_levels
        and c.get("casebook_count", 0) >= min_casebooks
    ]
    cases.sort(key=lambda c: c.get("casebook_count", 0), reverse=True)

    if limit:
        cases = cases[:limit]

    print(f"Cases to import (confidence >= {min_confidence}, casebooks >= {min_casebooks}): {len(cases)}")

    if dry_run:
        print("\nDRY RUN - would import:")
        print(f"  Casebooks: {len(casebooks)}")
        print(f"  Cases: {len(cases)}")
        print("\nTop cases:")
        for c in cases[:20]:
            print(f"  [{c['casebook_count']} books] {c['name']} | {c.get('citation', 'no cite')} (cluster {c['cluster_id']})")
        return

    # Connect to database
    print("\nConnecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Check if casebook tables exist
        tables_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'casebooks'
            )
        """)
        if not tables_exist:
            print("Casebook tables don't exist. Running migration...")
            migration_path = Path("migrations/002_casebooks.sql")
            if migration_path.exists():
                with open(migration_path) as f:
                    await conn.execute(f.read())
                print("Migration complete")
            else:
                print(f"ERROR: Migration file not found: {migration_path}")
                return

        # Step 1: Create casebook records
        print(f"\nCreating {len(casebooks)} casebook records...")
        slug_to_id = await create_casebooks(conn, casebooks)
        print(f"Created/updated {len(slug_to_id)} casebooks")

        if casebooks_only:
            print("\n--casebooks-only: Done.")
            return

        # Step 2: Handle fetch-text mode (update existing stubs)
        if fetch_text:
            await fetch_text_for_stubs(conn, cases, limit)
            return

        # Step 3: Import cases
        print(f"\nImporting {len(cases)} cases...")

        # Check which already exist
        existing_ids = set()
        for c in cases:
            row = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", c["cluster_id"])
            if row:
                existing_ids.add(c["cluster_id"])

        new_cases = [c for c in cases if c["cluster_id"] not in existing_ids]
        print(f"Already in DB: {len(existing_ids)}")
        print(f"New to import: {len(new_cases)}")

        imported = 0
        failed = 0

        async with httpx.AsyncClient() as client:
            for i, case in enumerate(new_cases, 1):
                cluster_id = case["cluster_id"]
                print(f"[{i}/{len(new_cases)}] {case['name'][:60]} (cluster {cluster_id})")

                # Get metadata from local SQLite (fast) instead of API
                meta = get_case_metadata_from_sqlite(cluster_id)

                title = case["name"]
                reporter_cite = case.get("citation_found") or case.get("citation")
                date_filed = case.get("date_filed")
                source_url = f"https://www.courtlistener.com/opinion/{cluster_id}/"

                if meta:
                    title = meta["title"] or title
                    reporter_cite = meta.get("reporter_cite") or reporter_cite
                    date_filed = meta.get("decision_date") or date_filed
                    source_url = meta.get("source_url") or source_url

                # Parse decision date
                decision_date = None
                if date_filed:
                    try:
                        decision_date = datetime.strptime(date_filed, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        pass

                # Fetch opinion text (unless --skip-opinions)
                content = None
                if not skip_opinions:
                    content = await fetch_opinion_text(client, cluster_id)
                    if content:
                        print(f"  Got {len(content):,} chars of opinion text")
                    else:
                        print(f"  No opinion text (stub)")
                    await asyncio.sleep(0.5)

                # Insert into cases table
                try:
                    await conn.execute("""
                        INSERT INTO cases (id, title, decision_date, reporter_cite, content, source_url, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            reporter_cite = COALESCE(EXCLUDED.reporter_cite, cases.reporter_cite),
                            content = COALESCE(EXCLUDED.content, cases.content),
                            updated_at = NOW()
                    """,
                        cluster_id,
                        title,
                        decision_date,
                        reporter_cite,
                        content or None,
                        source_url
                    )
                    imported += 1
                except Exception as e:
                    print(f"  ERROR inserting: {e}")
                    failed += 1

        # Step 4: Link cases to casebooks
        print(f"\nLinking cases to casebooks...")
        linked = 0

        # Re-extract case-to-casebook mappings from the Apify data
        # We need to re-parse since matched_cases.json only has subjects, not full casebook slugs
        # Instead, use the casebook-level data: for each casebook, find cases it contains
        # We'll match by quimbee_slug

        # Build a case slug -> cluster_id + name mapping from our matched cases
        slug_to_case = {}
        for c in cases:
            slug_to_case[c["quimbee_slug"]] = c

        # Re-read Apify data to get case-to-casebook links
        import re
        apify_path = Path("dataset_website-content-crawler_2025-12-15_23-16-39-940.json")
        if apify_path.exists():
            with open(apify_path) as f:
                apify_data = json.load(f)

            CASE_LINK = re.compile(r'\[([^\]]+)\]\(https://www\.quimbee\.com/cases/([^)]+)\)')

            for page in apify_data:
                url = page.get("url", "")
                match = re.match(r"https://www\.quimbee\.com/casebooks/([^/]+)/(.+)", url)
                if not match:
                    continue

                subject = match.group(1)
                casebook_slug = match.group(2)
                casebook_key = f"{subject}/{casebook_slug}"
                casebook_id = slug_to_id.get(casebook_key)

                if not casebook_id:
                    continue

                md = page.get("markdown", "")
                case_links = CASE_LINK.findall(md)

                for case_name, case_slug in case_links:
                    case_info = slug_to_case.get(case_slug)
                    if not case_info or not case_info.get("cluster_id"):
                        continue

                    try:
                        await conn.execute("""
                            INSERT INTO casebook_cases (casebook_id, case_id, case_name_in_book, citation_in_book)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (casebook_id, case_id) DO NOTHING
                        """, casebook_id, case_info["cluster_id"],
                            case_name.strip(), case_info.get("citation", ""))
                        linked += 1
                    except Exception as e:
                        # Foreign key errors expected for cases not yet imported
                        pass

        # Print results
        print(f"\n{'='*60}")
        print("IMPORT COMPLETE")
        print(f"{'='*60}")
        print(f"New cases imported: {imported}")
        print(f"Already in DB:     {len(existing_ids)}")
        print(f"Failed:            {failed}")
        print(f"Casebook links:    {linked}")
        print(f"{'='*60}")

        if imported > 0 and skip_opinions:
            print(f"\nStubs imported without opinion text.")
            print(f"Fetch text later with: python scripts/import_quimbee_cases.py --fetch-text")

        if imported > 0:
            print(f"\nNext: rebuild citations with:")
            print(f"  PROD_DATABASE_URL=\"...\" python3 scripts/import_citations_local.py")

    finally:
        await conn.close()


async def fetch_text_for_stubs(conn, cases, limit):
    """Fetch opinion text for existing stub cases that have no content."""
    cluster_ids = [c["cluster_id"] for c in cases if c.get("cluster_id")]

    # Find stubs in batches
    stubs = await conn.fetch("""
        SELECT id, title FROM cases
        WHERE id = ANY($1)
          AND (content IS NULL OR length(content) < 100)
        ORDER BY id
    """, cluster_ids)

    if limit:
        stubs = stubs[:limit]

    print(f"Found {len(stubs)} stubs needing opinion text")
    if not stubs:
        print("All cases already have opinion text!")
        return

    updated = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        for i, stub in enumerate(stubs, 1):
            print(f"[{i}/{len(stubs)}] {stub['title'][:60]}")

            content = await fetch_opinion_text(client, stub["id"])

            if content and len(content) > 100:
                try:
                    await conn.execute("""
                        UPDATE cases SET content = $1, updated_at = NOW()
                        WHERE id = $2
                    """, content, stub["id"])
                    updated += 1
                    print(f"  Updated with {len(content):,} chars")
                except Exception as e:
                    print(f"  ERROR: {e}")
                    failed += 1
            else:
                print(f"  No opinion text found")
                failed += 1

            await asyncio.sleep(1)

    print(f"\n{'='*50}")
    print(f"FETCH TEXT COMPLETE")
    print(f"{'='*50}")
    print(f"Updated: {updated}")
    print(f"Failed/no text: {failed}")


async def main():
    parser = argparse.ArgumentParser(description="Import matched Quimbee cases to production DB")
    parser.add_argument("--input", default=str(MATCHED_FILE),
                        help=f"Matched cases JSON (default: {MATCHED_FILE})")
    parser.add_argument("--limit", type=int, help="Max number of cases to import")
    parser.add_argument("--min-casebooks", type=int, default=1,
                        help="Only import cases appearing in N+ casebooks (default: 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without importing")
    parser.add_argument("--skip-opinions", action="store_true",
                        help="Import stubs only, fetch opinion text later")
    parser.add_argument("--fetch-text", action="store_true",
                        help="Fetch opinion text for existing stubs")
    parser.add_argument("--casebooks-only", action="store_true",
                        help="Only create casebook records, don't import cases")
    parser.add_argument("--exact-only", action="store_true",
                        help="Only import cases with 'exact' match confidence")

    args = parser.parse_args()

    await import_cases(
        input_file=Path(args.input),
        limit=args.limit,
        min_casebooks=args.min_casebooks,
        dry_run=args.dry_run,
        skip_opinions=args.skip_opinions,
        fetch_text=args.fetch_text,
        casebooks_only=args.casebooks_only,
        min_confidence="exact" if args.exact_only else "likely"
    )


if __name__ == "__main__":
    asyncio.run(main())
