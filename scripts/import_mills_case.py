#!/usr/bin/env python3
"""
Import Mills v. City of St. Louis (E.D. Mo. Jan. 30, 2026) from the RECAP archive.

Why this one needs a bespoke script: the opinion is not in CourtListener's curated
opinions database (it's RECAP-only, i.e. a PACER document someone paid for and donated),
so the normal cluster-id import path can't reach it. The docket is 4:25-cv-1219-MTS and
the memorandum-and-order is document #37.

Court opinions are public-domain government works, so there is no rights issue in
mirroring the text.

Usage:
    python3 scripts/import_mills_case.py --dry-run
    python3 scripts/import_mills_case.py
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from datetime import date

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")

RECAP_PDF_URL = (
    "https://storage.courtlistener.com/recap/gov.uscourts.moed.222529/"
    "gov.uscourts.moed.222529.37.0.pdf"
)
OPINION_MARKER = "[[COURTLISTENER_SUBOPINION {}]]".format(
    json.dumps(
        {
            "id": "recap:71099811:37",
            "type": None,
            "part": "majority",
            "author": "Matthew T. Schelp",
            "source_field": "recap_pdf",
        },
        separators=(",", ":"),
    )
)

CASE_ID = "manual-mills-v-city-of-st-louis"
TITLE = "Mills v. City of St. Louis"
DECISION_DATE = date(2026, 1, 30)
# No reporter cite: the order is Lexis-only (2026 U.S. Dist. LEXIS 19989). Leaving this
# NULL makes build_canonical_slug() fall back to the title slug, giving the clean URL
# /cases/mills-v-city-of-st-louis
REPORTER_CITE = None

METADATA = {
    "source": "recap",
    "cl_court": "E.D. Mo.",
    "docket_number": "4:25-cv-1219-MTS",
    "docket_id": 71099811,
    "pacer_case_id": "222529",
    "document_number": 37,
    "recap_pdf_url": RECAP_PDF_URL,
    "docket_url": (
        "https://www.courtlistener.com/docket/71099811/"
        "mills-v-city-of-st-louis-missouri/"
    ),
    "lexis_cite": "2026 U.S. Dist. LEXIS 19989",
    "note": (
        "RECAP-only; not present in CourtListener's opinions database. Imported for the "
        "AI-assisted pro se litigation research (companion to Jones v. Kankakee County "
        "Sheriff's Dep't, 164 F.4th 967)."
    ),
}


def fetch_opinion_text() -> str:
    """Download the RECAP PDF and extract its text with pdftotext."""
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "mills.pdf")
        req = urllib.request.Request(RECAP_PDF_URL, headers={"User-Agent": "tortwell-import"})
        with urllib.request.urlopen(req) as resp, open(pdf_path, "wb") as fh:
            fh.write(resp.read())

        result = subprocess.run(
            ["pdftotext", pdf_path, "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout


def sanity_check(text: str) -> None:
    """Fail loudly if the PDF isn't the document we think it is."""
    required = [
        "4:25-cv-01219-MTS",
        "THEODA E. MILLS",
        "CITY OF ST. LOUIS",
        "MEMORANDUM AND ORDER",
    ]
    missing = [needle for needle in required if needle not in text]
    if missing:
        sys.exit(f"Refusing to import: PDF text missing expected markers: {missing}")
    if len(text) < 5000:
        sys.exit(f"Refusing to import: extracted text suspiciously short ({len(text)} chars)")


def mark_opinion(text: str) -> str:
    """Identify the RECAP document as one verified opinion of the court."""
    return f"{OPINION_MARKER}\n{text.strip()}"


async def main(dry_run: bool) -> None:
    text = fetch_opinion_text()
    sanity_check(text)
    text = mark_opinion(text)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"Extracted opinion text: {len(text)} chars")
    print(f"First line: {text.strip().splitlines()[0]!r}")

    if dry_run:
        print("\n--- DRY RUN, nothing written ---")
        print(f"id:            {CASE_ID}")
        print(f"title:         {TITLE}")
        print(f"decision_date: {DECISION_DATE}")
        print(f"reporter_cite: {REPORTER_CITE}")
        print(f"source_url:    {RECAP_PDF_URL}")
        print(f"metadata:      {json.dumps(METADATA, indent=2)}")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        existing = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", CASE_ID)
        if existing:
            print(f"Case {CASE_ID} already exists — updating content/metadata.")
            await conn.execute(
                """
                UPDATE cases
                   SET title = $2,
                       decision_date = $3,
                       reporter_cite = $4,
                       content = $5,
                       metadata = $6,
                       source_url = $7,
                       content_hash = $8,
                       updated_at = NOW()
                 WHERE id = $1
                """,
                CASE_ID, TITLE, DECISION_DATE, REPORTER_CITE,
                text, json.dumps(METADATA), RECAP_PDF_URL, content_hash,
            )
        else:
            await conn.execute(
                """
                INSERT INTO cases
                    (id, title, decision_date, reporter_cite, content, metadata, source_url,
                     content_hash)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                CASE_ID, TITLE, DECISION_DATE, REPORTER_CITE,
                text, json.dumps(METADATA), RECAP_PDF_URL, content_hash,
            )
            print(f"Inserted {CASE_ID}")

        row = await conn.fetchrow(
            "SELECT id, title, decision_date, LENGTH(content) AS len FROM cases WHERE id = $1",
            CASE_ID,
        )
        print(f"Verified in DB: {dict(row)}")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
