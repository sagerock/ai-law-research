#!/usr/bin/env python3
"""
Backfill casebooks table with per-textbook entries from Quimbee Apify data.

The original import collapsed all casebooks into one row per subject.
This script creates proper per-textbook rows with full metadata
(book title, author, edition, ISBN) and re-links cases.

Usage:
    python scripts/backfill_textbooks.py --dry-run     # Preview changes
    python scripts/backfill_textbooks.py               # Run against local DB
    python scripts/backfill_textbooks.py --prod         # Run against production
"""

import argparse
import asyncio
import json
import os
import re
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv()

APIFY_DATA = Path("dataset_website-content-crawler_2025-12-15_23-16-39-940.json")
MATCHED_DATA = Path("data/quimbee/matched_cases.json")


def parse_apify_casebooks(apify_path: Path) -> dict:
    """Parse full textbook metadata and case lists from Apify scrape data."""
    with open(apify_path) as f:
        data = json.load(f)

    books = {}
    for page in data:
        url = page.get("url", "")
        md = page.get("markdown", "")
        if "Online Case Briefs Keyed to" not in md or "Thousands" in md:
            continue

        slug = url.rstrip("/").split("/")[-1]
        # Extract subject from URL: /casebooks/{subject}/{slug}
        parts = url.rstrip("/").split("/")
        subject_idx = parts.index("casebooks") + 1 if "casebooks" in parts else -1
        subject = parts[subject_idx] if subject_idx > 0 and subject_idx < len(parts) - 1 else None

        # Parse heading: # Subject Online Case Briefs Keyed to Book Title - Author, Edition Ed. \[ISBN isbn\]
        book_title = None
        author = None
        edition = None
        isbn = None

        for line in md.split("\n"):
            if "Keyed to" not in line:
                continue
            m = re.match(
                r'^#\s+.+?\s+Online Case Briefs Keyed to\s+(.+?)\s+-\s+(.+?)(?:,\s*(\d+(?:st|nd|rd|th))\s*Ed\.?)?\s*\\*\[ISBN\s*(\d+)\s*\\*\]',
                line
            )
            if m:
                book_title = m.group(1).strip()
                author = m.group(2).strip().rstrip(",")
                edition = m.group(3)
                isbn = m.group(4)
            break

        # Extract case slugs from links
        case_slugs = re.findall(
            r"\[.+?\]\(https://www\.quimbee\.com/cases/([^)]+)\)", md
        )

        if book_title:
            books[slug] = {
                "slug": slug,
                "subject": subject,
                "book_title": book_title,
                "author": author,
                "edition": edition,
                "isbn": isbn if isbn and len(isbn) >= 10 else None,
                "case_slugs": case_slugs,
            }

    return books


def build_slug_to_cluster(matched_path: Path) -> dict:
    """Build quimbee_slug -> cluster_id mapping from matched cases."""
    with open(matched_path) as f:
        data = json.load(f)

    mapping = {}
    for case in data.get("cases", []):
        if case.get("cluster_id"):
            mapping[case["quimbee_slug"]] = {
                "cluster_id": case["cluster_id"],
                "name": case["name"],
                "citation": case.get("citation"),
            }
    return mapping


async def backfill(dry_run: bool = False, prod: bool = False):
    """Create per-textbook casebook rows and link cases."""
    if prod:
        db_url = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not db_url or "railway" not in db_url:
            print("Error: Set PROD_DATABASE_URL for production backfill")
            return 1
    else:
        db_url = os.getenv("DATABASE_URL", "postgresql://localhost/legal_research")

    print("Parsing Apify data...")
    books = parse_apify_casebooks(APIFY_DATA)
    print(f"  Found {len(books)} textbooks with metadata")

    print("Building case slug -> cluster_id mapping...")
    slug_to_cluster = build_slug_to_cluster(MATCHED_DATA)
    print(f"  Found {len(slug_to_cluster)} matched cases")

    if dry_run:
        print("\n[DRY RUN — no database changes]\n")
        # Show summary
        with_edition = sum(1 for b in books.values() if b["edition"])
        with_isbn = sum(1 for b in books.values() if b["isbn"])
        total_links = sum(len(b["case_slugs"]) for b in books.values())
        resolvable = sum(
            1
            for b in books.values()
            for s in b["case_slugs"]
            if s in slug_to_cluster
        )
        print(f"  Textbooks: {len(books)} ({with_edition} with edition, {with_isbn} with ISBN)")
        print(f"  Case links: {total_links} total, {resolvable} resolvable to cluster_id")

        # Show subjects
        subjects = {}
        for b in books.values():
            subj = b["subject"] or "unknown"
            subjects[subj] = subjects.get(subj, 0) + 1
        print(f"\n  Subjects ({len(subjects)}):")
        for subj, count in sorted(subjects.items(), key=lambda x: -x[1])[:15]:
            print(f"    {subj}: {count} books")
        print(f"    ... and {len(subjects) - 15} more" if len(subjects) > 15 else "")
        return 0

    # Connect
    conn = await asyncpg.connect(db_url)
    print("Connected to database", flush=True)

    try:
        # Get existing cases in our DB
        rows = await conn.fetch("SELECT id FROM cases")
        existing_cases = {r["id"] for r in rows}
        print(f"  {len(existing_cases)} cases in database", flush=True)

        # Pre-build all casebook inserts and case link batches
        casebook_rows = []  # (full_title, subject, isbn, edition, authors, metadata, slug)
        for slug, book in books.items():
            edition_str = f", {book['edition']} Ed." if book["edition"] else ""
            full_title = f"{book['book_title']} ({book['author']}{edition_str})"
            casebook_rows.append((
                full_title,
                book["subject"],
                book["isbn"],
                f"{book['edition']} Ed." if book["edition"] else None,
                book["author"],
                json.dumps({"source": "quimbee", "quimbee_slug": slug}),
                slug,
            ))

        # Insert all casebooks in a transaction
        print(f"  Inserting {len(casebook_rows)} casebooks...", flush=True)
        slug_to_cb_id = {}
        async with conn.transaction():
            for row in casebook_rows:
                casebook_id = await conn.fetchval("""
                    INSERT INTO casebooks (title, subject, isbn, edition, authors, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (title) DO UPDATE SET
                        isbn = COALESCE(EXCLUDED.isbn, casebooks.isbn),
                        edition = COALESCE(EXCLUDED.edition, casebooks.edition),
                        authors = COALESCE(EXCLUDED.authors, casebooks.authors),
                        updated_at = NOW()
                    RETURNING id
                """, *row[:6])
                slug_to_cb_id[row[6]] = casebook_id
        print(f"  Created {len(slug_to_cb_id)} casebooks", flush=True)

        # Build all case link rows
        print("  Building case links...", flush=True)
        link_rows = []
        skipped = 0
        for slug, book in books.items():
            cb_id = slug_to_cb_id.get(slug)
            if not cb_id:
                continue
            for i, case_slug in enumerate(book["case_slugs"]):
                match = slug_to_cluster.get(case_slug)
                if not match or match["cluster_id"] not in existing_cases:
                    skipped += 1
                    continue
                link_rows.append((
                    cb_id, match["cluster_id"], match["name"],
                    match.get("citation"), i
                ))

        print(f"  Inserting {len(link_rows)} case links (skipped {skipped})...", flush=True)

        # Batch insert case links using executemany
        BATCH = 500
        linked = 0
        async with conn.transaction():
            for start in range(0, len(link_rows), BATCH):
                batch = link_rows[start:start + BATCH]
                for row in batch:
                    try:
                        await conn.execute("""
                            INSERT INTO casebook_cases
                                (casebook_id, case_id, case_name_in_book, citation_in_book, sort_order)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (casebook_id, case_id) DO UPDATE SET
                                sort_order = EXCLUDED.sort_order
                        """, *row)
                        linked += 1
                    except Exception:
                        pass
                print(f"    {min(start + BATCH, len(link_rows))}/{len(link_rows)} links...", flush=True)

        print(f"\nDone!", flush=True)
        print(f"  Casebooks created/updated: {len(slug_to_cb_id)}", flush=True)
        print(f"  Case links created: {linked}", flush=True)
        print(f"  Skipped (case not in DB): {skipped}", flush=True)

    finally:
        await conn.close()

    return 0


def main():
    parser = argparse.ArgumentParser(description="Backfill casebooks with per-textbook entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--prod", action="store_true", help="Run against production database")
    args = parser.parse_args()

    return asyncio.run(backfill(dry_run=args.dry_run, prod=args.prod))


if __name__ == "__main__":
    exit(main())
