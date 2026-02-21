#!/usr/bin/env python3
"""
Import cited-but-missing cases as stub entries (metadata only, no opinion text).

Reads data/cited_but_missing.json and inserts:
1. Stub case rows into `cases` (content=NULL)
2. Citation relationships into `citations`

Stubs are hidden from search (content IS NULL) and only discoverable
through citation network links. When a user generates an AI brief,
the backend fetches the full opinion from CourtListener and the case
"graduates" to full status.

Usage:
    # Import all matched cases (~11,752)
    python3 scripts/import_stub_cases.py

    # Only cases cited 2+ times (fewer, higher value)
    python3 scripts/import_stub_cases.py --min-citations 2

    # Limit to top N most-cited
    python3 scripts/import_stub_cases.py --limit 500

    # Preview without writing
    python3 scripts/import_stub_cases.py --dry-run

    # Combine flags
    python3 scripts/import_stub_cases.py --min-citations 3 --limit 100 --dry-run
"""

import asyncio
import argparse
import json
import os
import sys

import asyncpg
from dotenv import load_dotenv

load_dotenv()

PROD_DATABASE_URL = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "cited_but_missing.json")


async def import_stubs(min_citations: int = 1, limit: int = 0, dry_run: bool = False):
    """Import stub cases from cited_but_missing.json to production database."""

    # Load data
    with open(DATA_FILE, "r") as f:
        all_cases = json.load(f)

    # Filter to cases with cluster_ids
    matched = [c for c in all_cases if c.get("cluster_id")]
    print(f"Total entries in file: {len(all_cases)}")
    print(f"With CourtListener cluster_id: {len(matched)}")

    # Apply min-citations filter
    if min_citations > 1:
        matched = [c for c in matched if c.get("times_cited", 0) >= min_citations]
        print(f"With >= {min_citations} citations: {len(matched)}")

    # Sort by times_cited descending (most important first)
    matched.sort(key=lambda c: c.get("times_cited", 0), reverse=True)

    # Apply limit
    if limit > 0:
        matched = matched[:limit]
        print(f"Limited to top {limit}")

    print(f"\nCases to import: {len(matched)}")

    if not matched:
        print("No cases to import.")
        return

    # Show top 10 preview
    print(f"\nTop cases by citation count:")
    for c in matched[:10]:
        print(f"  [{c['times_cited']:3d}x] {c['case_name']} ({c['citation']})")
    if len(matched) > 10:
        print(f"  ... and {len(matched) - 10} more")

    if dry_run:
        print(f"\nDRY RUN - No changes will be made")

        # Count citation relationships that would be created
        total_citations = sum(len(c.get("cited_by_cluster_ids", [])) for c in matched)
        print(f"Citation relationships to insert: {total_citations}")
        return

    if not PROD_DATABASE_URL:
        print("\nERROR: No database URL found")
        print("Set PROD_DATABASE_URL or DATABASE_URL environment variable")
        sys.exit(1)

    print(f"\nConnecting to database...")
    conn = await asyncpg.connect(PROD_DATABASE_URL)

    try:
        # Check which cases already exist
        existing_ids = set()
        all_stub_ids = [c["cluster_id"] for c in matched]

        # Batch check in chunks of 500
        for i in range(0, len(all_stub_ids), 500):
            chunk = all_stub_ids[i:i+500]
            rows = await conn.fetch(
                "SELECT id FROM cases WHERE id = ANY($1)",
                chunk
            )
            existing_ids.update(r["id"] for r in rows)

        new_cases = [c for c in matched if c["cluster_id"] not in existing_ids]
        print(f"Already in database: {len(existing_ids)}")
        print(f"New stubs to insert: {len(new_cases)}")

        # Insert stub cases
        inserted = 0
        for c in new_cases:
            metadata = {
                "courtlistener_id": c["cluster_id"],
                "citation": c["citation"],
                "citation_count": c["times_cited"],
                "cited_by_cluster_ids": c.get("cited_by_cluster_ids", []),
                "stub": True,
            }
            if c.get("year"):
                metadata["year"] = c["year"]

            try:
                await conn.execute(
                    """
                    INSERT INTO cases (id, title, decision_date, reporter_cite, content, metadata, source_url)
                    VALUES ($1, $2, $3, $4, NULL, $5, $6)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    c["cluster_id"],
                    c["case_name"],
                    c.get("date_filed"),  # already a string like "1966-06-13"
                    c["citation"],
                    json.dumps(metadata),
                    f"https://www.courtlistener.com/opinion/{c['cluster_id']}/",
                )
                inserted += 1
            except Exception as e:
                print(f"  Error inserting {c['case_name']}: {e}")

        print(f"Inserted {inserted} stub cases")

        # Insert citation relationships
        # For each stub, its cited_by_cluster_ids are existing cases that cite it
        citation_count = 0
        citation_errors = 0

        for c in matched:
            target_id = c["cluster_id"]
            for source_id in c.get("cited_by_cluster_ids", []):
                try:
                    await conn.execute(
                        """
                        INSERT INTO citations (source_case_id, target_case_id, signal, confidence)
                        VALUES ($1, $2, 'cited', 0.8)
                        ON CONFLICT DO NOTHING
                        """,
                        source_id,
                        target_id,
                    )
                    citation_count += 1
                except Exception as e:
                    # Foreign key errors are expected if the source case isn't in DB
                    citation_errors += 1

        print(f"Inserted {citation_count} citation relationships ({citation_errors} skipped)")

        # Final stats
        total_cases = await conn.fetchval("SELECT COUNT(*) FROM cases")
        total_stubs = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE content IS NULL")
        total_citations = await conn.fetchval("SELECT COUNT(*) FROM citations")

        print(f"\n{'='*50}")
        print("IMPORT COMPLETE")
        print(f"{'='*50}")
        print(f"Total cases in database: {total_cases}")
        print(f"  Stub cases (no content): {total_stubs}")
        print(f"  Full cases (with content): {total_cases - total_stubs}")
        print(f"Total citation relationships: {total_citations}")
        print(f"{'='*50}")

    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Import cited-but-missing cases as stubs"
    )
    parser.add_argument(
        "--min-citations", type=int, default=1,
        help="Only import cases cited at least N times (default: 1)"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit to top N most-cited cases (default: all)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing to database"
    )

    args = parser.parse_args()
    await import_stubs(
        min_citations=args.min_citations,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    asyncio.run(main())
