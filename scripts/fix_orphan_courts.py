#!/usr/bin/env python3
"""
Fix cases with orphaned court_ids (pointing to non-existent courts rows).

Finds cases where court_id references a row that doesn't exist in the courts
table, infers the correct court from the reporter citation, and updates.

Usage:
    DATABASE_URL=postgres://... python scripts/fix_orphan_courts.py [--dry-run]
"""

import asyncio
import asyncpg
import os
import re
import sys

# Reporter abbreviation → (court_name, jurisdiction, level)
REPORTER_TO_COURT = {
    # Supreme Court
    "U.S.": ("Supreme Court of the United States", "federal", "supreme"),
    "S. Ct.": ("Supreme Court of the United States", "federal", "supreme"),
    "L. Ed.": ("Supreme Court of the United States", "federal", "supreme"),
    "L. Ed. 2d": ("Supreme Court of the United States", "federal", "supreme"),
    "How.": ("Supreme Court of the United States", "federal", "supreme"),
    "Wheat.": ("Supreme Court of the United States", "federal", "supreme"),
    "Cranch": ("Supreme Court of the United States", "federal", "supreme"),
    "Wall.": ("Supreme Court of the United States", "federal", "supreme"),
    "Dall.": ("Supreme Court of the United States", "federal", "supreme"),
    "Pet.": ("Supreme Court of the United States", "federal", "supreme"),
    "Black": ("Supreme Court of the United States", "federal", "supreme"),

    # Federal Circuit Courts of Appeals
    "F.": ("U.S. Court of Appeals", "federal", "appellate"),
    "F.2d": ("U.S. Court of Appeals", "federal", "appellate"),
    "F.3d": ("U.S. Court of Appeals", "federal", "appellate"),
    "F.4th": ("U.S. Court of Appeals", "federal", "appellate"),
    "F. App'x": ("U.S. Court of Appeals", "federal", "appellate"),

    # Federal District Courts
    "F. Supp.": ("U.S. District Court", "federal", "trial"),
    "F. Supp. 2d": ("U.S. District Court", "federal", "trial"),
    "F. Supp. 3d": ("U.S. District Court", "federal", "trial"),
    "F.R.D.": ("U.S. District Court", "federal", "trial"),

    # Specialty Federal Courts
    "B.R.": ("U.S. Bankruptcy Court", "federal", "trial"),
    "T.C.": ("U.S. Tax Court", "federal", "trial"),

    # State reporters
    "N.Y.": ("New York Court of Appeals", "state", "supreme"),
    "N.Y.2d": ("New York Court of Appeals", "state", "supreme"),
    "N.Y.3d": ("New York Court of Appeals", "state", "supreme"),
    "A.D.": ("New York Appellate Division", "state", "appellate"),
    "A.D.2d": ("New York Appellate Division", "state", "appellate"),
    "A.D.3d": ("New York Appellate Division", "state", "appellate"),
    "Cal.": ("Supreme Court of California", "state", "supreme"),
    "Cal. 2d": ("Supreme Court of California", "state", "supreme"),
    "Cal. 3d": ("Supreme Court of California", "state", "supreme"),
    "Cal. 4th": ("Supreme Court of California", "state", "supreme"),
    "Cal. 5th": ("Supreme Court of California", "state", "supreme"),
    "Cal. App.": ("California Court of Appeal", "state", "appellate"),
    "Cal. App. 2d": ("California Court of Appeal", "state", "appellate"),
    "Cal. App. 3d": ("California Court of Appeal", "state", "appellate"),
    "Cal. App. 4th": ("California Court of Appeal", "state", "appellate"),
    "Cal. App. 5th": ("California Court of Appeal", "state", "appellate"),
    "Cal. Rptr.": ("California Court of Appeal", "state", "appellate"),
    "Cal. Rptr. 2d": ("California Court of Appeal", "state", "appellate"),
    "Cal. Rptr. 3d": ("California Court of Appeal", "state", "appellate"),
    "Ill.": ("Supreme Court of Illinois", "state", "supreme"),
    "Ill. 2d": ("Supreme Court of Illinois", "state", "supreme"),
    "Ill. App.": ("Illinois Appellate Court", "state", "appellate"),
    "Ill. App. 2d": ("Illinois Appellate Court", "state", "appellate"),
    "Ill. App. 3d": ("Illinois Appellate Court", "state", "appellate"),
    "Mass.": ("Supreme Judicial Court of Massachusetts", "state", "supreme"),
    "Pa.": ("Supreme Court of Pennsylvania", "state", "supreme"),
    "Ohio St.": ("Supreme Court of Ohio", "state", "supreme"),
    "Ohio St. 2d": ("Supreme Court of Ohio", "state", "supreme"),
    "Ohio St. 3d": ("Supreme Court of Ohio", "state", "supreme"),

    # Regional reporters (can't determine specific state court)
    "N.E.": ("State Court", "state", "unknown"),
    "N.E.2d": ("State Court", "state", "unknown"),
    "N.E.3d": ("State Court", "state", "unknown"),
    "N.W.": ("State Court", "state", "unknown"),
    "N.W.2d": ("State Court", "state", "unknown"),
    "S.E.": ("State Court", "state", "unknown"),
    "S.E.2d": ("State Court", "state", "unknown"),
    "S.W.": ("State Court", "state", "unknown"),
    "S.W.2d": ("State Court", "state", "unknown"),
    "S.W.3d": ("State Court", "state", "unknown"),
    "So.": ("State Court", "state", "unknown"),
    "So. 2d": ("State Court", "state", "unknown"),
    "So. 3d": ("State Court", "state", "unknown"),
    "P.": ("State Court", "state", "unknown"),
    "P.2d": ("State Court", "state", "unknown"),
    "P.3d": ("State Court", "state", "unknown"),
    "A.": ("State Court", "state", "unknown"),
    "A.2d": ("State Court", "state", "unknown"),
    "A.3d": ("State Court", "state", "unknown"),

    # Daily journals (usually SCOTUS during same term)
    "Daily Journal DAR": ("Supreme Court of the United States", "federal", "supreme"),
}


# Well-known cases where court can be inferred from title (when citation is missing)
# Format: substring in title → (court_name, jurisdiction, level)
SCOTUS_BY_TITLE = [
    # Well-known SCOTUS cases in the Unknown Court bucket
    "v. Nixon", "v. Morrison", "v. O'Brien", "v. Lopez",
    "AT&T Mobility", "Concepcion",
    "National Federation of Independent Business", "Sebelius",
    "Shady Grove", "Allstate",
    "Iqbal v. Ashcroft", "Ashcroft v. Iqbal",
    "J. McIntyre Machinery", "Nicastro",
    "Village of Euclid", "Ambler Realty",
    "West Coast Hotel", "Parrish",
    "Youngstown Sheet", "Sawyer",
    "Brandenburg v. Ohio",
    "Flores v. City of Boerne",
    "Trump v. Mazars",
    "Amchem Products", "v. Windsor",
    "Goodyear Dunlop", "v. Brown",
]

# Cases that are NOT SCOTUS but can be identified by title
TITLE_TO_COURT = {
    "Pierson v. Post": ("New York Supreme Court of Judicature", "state", "supreme"),
    "People of Michigan": ("Michigan Supreme Court", "state", "supreme"),
    "Fleming v. MacKenzie River Pizza": ("Montana Supreme Court", "state", "supreme"),
}


def infer_court(reporter_cite: str, title: str = "") -> tuple[str, str, str] | None:
    """Infer court from title or reporter citation. Returns (name, jurisdiction, level) or None."""
    # Try title-based matching first (more reliable for known landmark cases)
    if title:
        for pattern, court_info in TITLE_TO_COURT.items():
            if pattern in title:
                return court_info

        for pattern in SCOTUS_BY_TITLE:
            if pattern in title:
                return ("Supreme Court of the United States", "federal", "supreme")

    # Fall back to citation-based inference
    if reporter_cite:
        for abbr in sorted(REPORTER_TO_COURT, key=len, reverse=True):
            if abbr in reporter_cite:
                return REPORTER_TO_COURT[abbr]

    return None


async def get_or_create_court(conn, name: str, jurisdiction: str, level: str) -> int:
    """Get existing court ID or create new one."""
    court_id = await conn.fetchval(
        "SELECT id FROM courts WHERE name = $1", name
    )
    if court_id:
        return court_id

    court_id = await conn.fetchval(
        """INSERT INTO courts (name, jurisdiction, level)
           VALUES ($1, $2, $3)
           ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
           RETURNING id""",
        name, jurisdiction, level
    )
    print(f"  Created court: {name} (id={court_id})")
    return court_id


async def main():
    dry_run = "--dry-run" in sys.argv

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = await asyncpg.connect(database_url)

    try:
        # Find cases with orphaned court_ids (no matching courts row)
        orphans = await conn.fetch("""
            SELECT c.id, c.title, c.court_id, c.reporter_cite
            FROM cases c
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE c.court_id IS NOT NULL
              AND ct.id IS NULL
            ORDER BY c.title
        """)

        # Also find cases assigned to "Unknown Court"
        unknown_court = await conn.fetch("""
            SELECT c.id, c.title, c.court_id, c.reporter_cite
            FROM cases c
            JOIN courts ct ON c.court_id = ct.id
            WHERE ct.name = 'Unknown Court'
            ORDER BY c.title
        """)

        all_bad = list(orphans) + list(unknown_court)
        print(f"Found {len(orphans)} cases with orphaned court_ids")
        print(f"Found {len(unknown_court)} cases assigned to 'Unknown Court'")
        print(f"Total to fix: {len(all_bad)}\n")

        if not all_bad:
            print("Nothing to fix!")
            return

        # Also report cases with NULL court_id
        null_court = await conn.fetchval(
            "SELECT COUNT(*) FROM cases WHERE court_id IS NULL"
        )
        if null_court:
            print(f"(Also {null_court} cases with NULL court_id — not handled by this script)\n")

        # Show a sample of what we're fixing
        print("Cases to fix:")
        for row in all_bad[:10]:
            print(f"  {row['id']:>8s}  {row['title'][:55]:55s}  {row['reporter_cite'] or '(no cite)'}")
        if len(all_bad) > 10:
            print(f"  ... and {len(all_bad) - 10} more\n")

        # Fix each case
        fixed = 0
        skipped = 0
        for row in all_bad:
            court_info = infer_court(row["reporter_cite"], row["title"])
            if not court_info:
                print(f"  SKIP: Can't infer court for {row['title']} (cite: {row['reporter_cite']})")
                skipped += 1
                continue

            name, jurisdiction, level = court_info

            if dry_run:
                print(f"  WOULD FIX: {row['title']} → {name}")
                fixed += 1
            else:
                court_id = await get_or_create_court(conn, name, jurisdiction, level)
                await conn.execute(
                    "UPDATE cases SET court_id = $1 WHERE id = $2",
                    court_id, row["id"]
                )
                print(f"  FIXED: {row['title']} → {name} (court_id={court_id})")
                fixed += 1

        print(f"\n{'DRY RUN — ' if dry_run else ''}Done: {fixed} fixed, {skipped} skipped")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
