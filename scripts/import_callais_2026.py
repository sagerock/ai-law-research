#!/usr/bin/env python3
"""
Voting Rights Act pair from Sage's Con Law reading (2026-09-26):

  - Louisiana v. Callais, 146 S. Ct. 1131 (Apr. 29, 2026)   [cluster 10850261]
    Imported as a stub; POST /api/v1/cases/10850261/fetch-opinion then hydrates it
    through the canonical CourtListener assembler (same path as the 2026-09-05
    standing-case imports). The later "Revisions: 5/04/26" cluster (10852760)
    only corrects the syllabus's argument dates, so the canonical cluster is used.
    The S. Ct. cite comes from Sage's Westlaw excerpt; CourtListener has no
    reporter cite yet and the U.S. Reports page is not assigned.
  - The existing 10618593 row is the June 27, 2025 order restoring Callais to the
    calendar for reargument. It is retitled so it no longer claims the name slug
    "louisiana-v-callais" or reads as the merits decision in search.
  - Shelby County v. Holder (931614) carried only its S. Ct. cite, so "570 U.S. 529"
    found nothing. Its reporter_cite now follows the U.S.-first convention used by
    other Supreme Court rows; the old 133-sct-2612 slug still resolves. Its S3 copy
    lacked sub-opinion markers, so the canonical CourtListener assembly is stored.

Idempotent. Run from repo root:  python scripts/import_callais_2026.py [--dry-run]
Requires PROD_DATABASE_URL in .env / environment.
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import date

import asyncpg

CALLAIS = {
    "id": "10850261",
    "title": "Louisiana v. Callais",
    "court_id": 13,  # Supreme Court of the United States
    "docket_number": "No. 24-109",
    "decision_date": date(2026, 4, 29),
    "reporter_cite": "146 S. Ct. 1131",
    "source_url": "https://www.courtlistener.com/opinion/10850261/louisiana-v-callais/",
    "metadata": {
        "source": "courtlistener_api",
        "subject": "constitutional-law",
        "reference_url": "https://www.supremecourt.gov/opinions/25pdf/24-109_new_jifl.pdf",
        "class_material": "Louisiana v Callais-edited 09.26.docx",
        "precedential_status": "Published",
        "courtlistener_docket_id": 69779623,
        "courtlistener_cluster_id": 10850261,
        "stub": True,
    },
}
REARGUMENT_ORDER_ID = "10618593"
REARGUMENT_ORDER_TITLE = "Louisiana v. Callais (order restoring case for reargument)"
SHELBY_ID = "931614"
SHELBY_CITE = "570 U.S. 529, 133 S. Ct. 2612, 186 L. Ed. 2d 651 (2013)"


def load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip('"'))


async def main(dry_run: bool):
    load_env()
    db_url = os.getenv("PROD_DATABASE_URL")
    if not db_url:
        sys.exit("ERROR: PROD_DATABASE_URL not set")

    conn = await asyncpg.connect(db_url)
    try:
        async with conn.transaction():
            if await conn.fetchval("SELECT 1 FROM cases WHERE id = $1", CALLAIS["id"]):
                print(f"skip (exists): {CALLAIS['title']} ({CALLAIS['id']})")
            else:
                await conn.execute(
                    """INSERT INTO cases (id, title, court_id, docket_number, decision_date,
                                          reporter_cite, precedential, source_url, metadata,
                                          created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, $6, TRUE, $7, $8, NOW(), NOW())""",
                    CALLAIS["id"], CALLAIS["title"], CALLAIS["court_id"],
                    CALLAIS["docket_number"], CALLAIS["decision_date"],
                    CALLAIS["reporter_cite"], CALLAIS["source_url"],
                    json.dumps(CALLAIS["metadata"]),
                )
                print(f"imported stub: {CALLAIS['title']} ({CALLAIS['id']})")

            status = await conn.execute(
                "UPDATE cases SET title = $1, updated_at = NOW() "
                "WHERE id = $2 AND title = 'Louisiana v. Callais'",
                REARGUMENT_ORDER_TITLE, REARGUMENT_ORDER_ID,
            )
            print(f"retitle reargument order {REARGUMENT_ORDER_ID}: {status}")

            status = await conn.execute(
                "UPDATE cases SET reporter_cite = $1, updated_at = NOW() "
                "WHERE id = $2 AND reporter_cite = '133 S. Ct. 2612'",
                SHELBY_CITE, SHELBY_ID,
            )
            print(f"Shelby County reporter_cite {SHELBY_ID}: {status}")

            # Shelby's S3 slip-opinion copy has no sub-opinion markers, so its majority
            # passages read as generic "opinion" and brief validation refused a dissent
            # claim. Store the canonical typed assembly in Postgres, which the loader
            # prefers over S3.
            if await conn.fetchval(
                "SELECT content IS NULL FROM cases WHERE id = $1", SHELBY_ID
            ):
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
                from courtlistener_opinions import fetch_courtlistener_document

                document = await fetch_courtlistener_document(
                    SHELBY_ID, os.environ["COURTLISTENER_API_KEY"]
                )
                status = await conn.execute(
                    "UPDATE cases SET content = $1, content_hash = $2, updated_at = NOW() "
                    "WHERE id = $3 AND content IS NULL",
                    document.text,
                    hashlib.sha256(document.text.encode("utf-8")).hexdigest(),
                    SHELBY_ID,
                )
                print(f"Shelby County canonical source ({len(document.text)} chars): {status}")

            if dry_run:
                raise RuntimeError("dry run: rolling back")
    except RuntimeError as e:
        print(e)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
