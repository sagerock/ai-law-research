#!/usr/bin/env python3
"""
Extract cases from Quimbee Apify data and match against local CourtListener SQLite.

Parses all casebook pages from the scraped Apify JSON, extracts case names + citations,
deduplicates by Quimbee slug, and matches against citations.db using citation-based
matching (volume/reporter/page) with FTS name fallback.

Usage:
    python scripts/match_quimbee_cases.py
    python scripts/match_quimbee_cases.py --subject torts
    python scripts/match_quimbee_cases.py --verbose
    python scripts/match_quimbee_cases.py --output data/quimbee/matched_cases.json
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Paths
APIFY_FILE = Path("dataset_website-content-crawler_2025-12-15_23-16-39-940.json")
DB_PATH = Path("data/courtlistener/citations.db")
DEFAULT_OUTPUT = Path("data/quimbee/matched_cases.json")

# Regex: case link followed by citation on next line
CASE_WITH_CITE = re.compile(
    r'\[([^\]]+)\]\(https://www\.quimbee\.com/cases/([^)]+)\)\s*\n\s*\n\s*([\d].*?)(?:\n|$)',
    re.MULTILINE
)
CASE_LINK_ONLY = re.compile(
    r'\[([^\]]+)\]\(https://www\.quimbee\.com/cases/([^)]+)\)'
)


def normalize_citation(citation: str) -> dict:
    """
    Parse a citation string into components for searching.
    Returns dict with volume, reporter, page, year.

    Examples:
        "60 Mass. 292 (1850)" -> {volume: 60, reporter: "Mass.", page: 292, year: 1850}
        "376 U.S. 254" -> {volume: 376, reporter: "U.S.", page: 254}
    """
    result = {
        "volume": None,
        "reporter": None,
        "page": None,
        "year": None,
        "raw": citation
    }

    # Extract year if present (usually in parentheses at end)
    year_match = re.search(r'\((\d{4})\)', citation)
    if year_match:
        result["year"] = int(year_match.group(1))

    # Common citation pattern: volume reporter page
    cite_pattern = r'^(\d+)\s+([A-Za-z\.\s\d]+?)\s+(\d+)'
    match = re.match(cite_pattern, citation)
    if match:
        result["volume"] = int(match.group(1))
        result["reporter"] = match.group(2).strip()
        result["page"] = int(match.group(3))

    return result


def extract_cases_from_apify(json_path: Path, subject_filter: str = None) -> tuple[list[dict], list[dict]]:
    """
    Extract all cases from Apify JSON, organized by Quimbee slug.

    Returns:
        (cases_list, casebooks_list) where cases_list is deduplicated by slug
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    # slug -> case info
    cases_by_slug = {}
    # casebook slug -> casebook info
    casebooks = {}

    for page in data:
        url = page.get("url", "")
        match = re.match(r"https://www\.quimbee\.com/casebooks/([^/]+)/(.+)", url)
        if not match:
            continue

        subject = match.group(1)
        casebook_slug = match.group(2)

        if subject_filter and subject != subject_filter:
            continue

        md = page.get("markdown", "")

        # Extract casebook metadata
        title_match = re.search(r"# (.+?) Online Case Briefs", md)
        casebook_name = title_match.group(1).strip() if title_match else casebook_slug

        isbn_match = re.search(r"\*\*ISBN-13:\*\* (\d+)", md)
        isbn = isbn_match.group(1) if isbn_match else None

        # Extract edition from title
        edition_match = re.search(r",?\s*(\d+(?:st|nd|rd|th))\s+Ed", casebook_name)
        edition = edition_match.group(1) if edition_match else None

        # Extract cases WITH citations (primary method)
        found_cases = CASE_WITH_CITE.findall(md)

        # Track which slugs we found with citations
        found_slugs = {slug for _, slug, _ in found_cases}

        # Also find case links without citations as fallback
        all_links = CASE_LINK_ONLY.findall(md)
        for name, slug in all_links:
            if slug not in found_slugs:
                found_cases.append((name, slug, ""))

        if not found_cases:
            continue

        # Record casebook
        casebook_key = f"{subject}/{casebook_slug}"
        casebooks[casebook_key] = {
            "slug": casebook_slug,
            "title": casebook_name,
            "subject": subject,
            "isbn": isbn,
            "edition": edition,
            "case_count": len(found_cases),
            "url": url
        }

        # Record cases
        for name, slug, citation in found_cases:
            citation = citation.strip()
            if slug not in cases_by_slug:
                cases_by_slug[slug] = {
                    "quimbee_slug": slug,
                    "name": name.strip(),
                    "citation": citation,
                    "subjects": set(),
                    "casebook_slugs": set(),
                    "casebook_count": 0
                }
            # Update with citation if we have one and existing doesn't
            if citation and not cases_by_slug[slug]["citation"]:
                cases_by_slug[slug]["citation"] = citation
            cases_by_slug[slug]["subjects"].add(subject)
            cases_by_slug[slug]["casebook_slugs"].add(casebook_key)

    # Finalize: convert sets to lists, compute casebook_count
    cases_list = []
    for slug, info in cases_by_slug.items():
        info["casebook_count"] = len(info["casebook_slugs"])
        info["subjects"] = sorted(info["subjects"])
        del info["casebook_slugs"]  # Don't need in output
        cases_list.append(info)

    # Sort by casebook_count descending (most popular first)
    cases_list.sort(key=lambda c: c["casebook_count"], reverse=True)

    casebooks_list = sorted(casebooks.values(), key=lambda c: c["case_count"], reverse=True)

    return cases_list, casebooks_list


def search_local_db(
    conn: sqlite3.Connection,
    case_name: str,
    citation: str,
    verbose: bool = False
) -> Optional[dict]:
    """
    Search local SQLite database for a case by citation, with name fallback.
    Returns match dict or None.
    """
    cursor = conn.cursor()
    parsed = normalize_citation(citation) if citation else {"volume": None, "reporter": None, "page": None, "year": None, "raw": ""}

    # Strategy 1: Search by volume/reporter/page in citations table
    if parsed["volume"] and parsed["page"]:
        search_reporter = None
        if parsed.get("reporter"):
            search_reporter = parsed["reporter"].strip().rstrip(".")

        if search_reporter:
            cursor.execute("""
                SELECT c.id, c.case_name, c.case_name_full, c.date_filed,
                       ci.volume, ci.reporter, ci.page
                FROM citations ci
                JOIN clusters c ON ci.cluster_id = c.id
                WHERE ci.volume = ? AND ci.page = ? AND ci.reporter LIKE ?
                LIMIT 10
            """, (parsed["volume"], parsed["page"], f"{search_reporter}%"))
        else:
            cursor.execute("""
                SELECT c.id, c.case_name, c.case_name_full, c.date_filed,
                       ci.volume, ci.reporter, ci.page
                FROM citations ci
                JOIN clusters c ON ci.cluster_id = c.id
                WHERE ci.volume = ? AND ci.page = ?
                LIMIT 20
            """, (parsed["volume"], parsed["page"]))

        results = cursor.fetchall()

        if results:
            for row in results:
                cluster_id, db_case_name, case_name_full, date_filed, volume, reporter, page = row

                result_name = (db_case_name or "").lower()
                search_name = case_name.lower()

                def get_first_party(name):
                    parts = re.split(r'\s+v\.?\s+', name.lower())
                    return parts[0].split()[0] if parts and parts[0].split() else ""

                result_party = get_first_party(result_name)
                search_party = get_first_party(search_name)

                # Calculate match score
                score = 50  # Base score for volume/page match
                confidence = "likely"

                # Check reporter match
                if parsed.get("reporter"):
                    parsed_reporter = parsed["reporter"].lower().replace(".", "").replace(" ", "")
                    result_reporter = (reporter or "").lower().replace(".", "").replace(" ", "")
                    if parsed_reporter == result_reporter:
                        score += 25
                        confidence = "exact"

                # Check party name match
                if result_party and search_party and result_party == search_party:
                    score += 20
                    confidence = "exact"
                elif result_party and search_party and (
                    result_party in search_name or search_party in result_name
                ):
                    score += 15

                # Check year match
                if parsed.get("year") and date_filed:
                    try:
                        result_year = int(date_filed.split("-")[0]) if "-" in date_filed else None
                        if result_year == parsed["year"]:
                            score += 15
                    except (ValueError, IndexError):
                        pass

                if verbose:
                    cite_str = f"{volume} {reporter} {page}"
                    print(f"    Local match: {db_case_name} [{cite_str}] (score: {score})")

                if score >= 50:
                    return {
                        "cluster_id": str(cluster_id),
                        "case_name": db_case_name or case_name_full,
                        "date_filed": date_filed,
                        "citation_found": f"{volume} {reporter} {page}",
                        "confidence": confidence
                    }

    # Strategy 2: Full-text search on case name
    first_party = case_name.split(' v. ')[0].strip() if ' v. ' in case_name else case_name
    first_party = re.sub(r',?\s*(Inc\.|Corp\.|Co\.|Ltd\.)$', '', first_party).strip()
    first_party = first_party.replace('"', '""')

    try:
        cursor.execute("""
            SELECT c.id, c.case_name, c.case_name_full, c.date_filed
            FROM clusters_fts fts
            JOIN clusters c ON fts.rowid = c.id
            WHERE clusters_fts MATCH ?
            LIMIT 30
        """, (f'"{first_party}"',))

        results = cursor.fetchall()

        for row in results:
            cluster_id, db_case_name, case_name_full, date_filed = row
            result_name = (db_case_name or "").lower()

            # Check year match
            year_match = False
            if parsed.get("year") and date_filed:
                try:
                    result_year = int(date_filed.split("-")[0]) if "-" in date_filed else None
                    if result_year and abs(result_year - parsed["year"]) <= 1:
                        year_match = True
                except (ValueError, IndexError):
                    pass

            # Check if both party names appear
            if ' v. ' in case_name:
                parties = case_name.lower().split(' v. ')
                first_in = parties[0].split()[0] in result_name if parties[0].split() else False
                second_in = parties[1].split()[0] in result_name if len(parties) > 1 and parties[1].split() else False

                if first_in and second_in and (year_match or not parsed.get("year")):
                    # Get citations for this cluster
                    cursor.execute("""
                        SELECT volume, reporter, page FROM citations WHERE cluster_id = ? LIMIT 5
                    """, (cluster_id,))
                    cite_rows = cursor.fetchall()
                    citation_found = f"{cite_rows[0][0]} {cite_rows[0][1]} {cite_rows[0][2]}" if cite_rows else None

                    if verbose:
                        print(f"    FTS match: {db_case_name} (parties+year)")

                    return {
                        "cluster_id": str(cluster_id),
                        "case_name": db_case_name or case_name_full,
                        "date_filed": date_filed,
                        "citation_found": citation_found,
                        "confidence": "likely"
                    }

    except sqlite3.OperationalError as e:
        if verbose:
            print(f"    FTS error: {e}")

    return None


def check_existing_in_db(conn: sqlite3.Connection, cases: list[dict]) -> set:
    """Check which cluster_ids already exist in our production database.
    This is a no-op for matching — we just flag them in the output."""
    # We can't check production DB from here, so we'll mark this in the import step
    return set()


def main():
    parser = argparse.ArgumentParser(
        description="Extract and match Quimbee cases against CourtListener"
    )
    parser.add_argument("--input", default=str(APIFY_FILE),
                        help=f"Apify JSON file (default: {APIFY_FILE})")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT),
                        help=f"Output JSON file (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--subject", help="Only process specific subject slug")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose matching output")
    parser.add_argument("--limit", type=int,
                        help="Limit number of cases to match (for testing)")
    parser.add_argument("--no-match", action="store_true",
                        help="Extract only, skip CourtListener matching")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        return 1

    # Step 1: Extract cases from Apify data
    print("=" * 60)
    print("QUIMBEE CASE MATCHER")
    print("=" * 60)
    print(f"\nReading: {input_path}")

    cases, casebooks = extract_cases_from_apify(input_path, subject_filter=args.subject)

    print(f"Casebooks: {len(casebooks)}")
    print(f"Unique cases: {len(cases)}")

    # Count cases with citations
    with_citations = sum(1 for c in cases if c["citation"])
    print(f"Cases with citations: {with_citations} ({100*with_citations/len(cases):.1f}%)")

    # Show subject breakdown
    subject_counts = defaultdict(int)
    for c in cases:
        for s in c["subjects"]:
            subject_counts[s] += 1
    print(f"\nSubjects ({len(subject_counts)}):")
    for subj, count in sorted(subject_counts.items(), key=lambda x: -x[1]):
        print(f"  {subj}: {count}")

    if args.no_match:
        # Save without matching
        output = {
            "stats": {
                "total": len(cases),
                "with_citations": with_citations,
                "matched": 0,
                "unmatched": len(cases)
            },
            "cases": cases,
            "casebooks": casebooks
        }
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nSaved to: {output_path}")
        return 0

    # Step 2: Match against CourtListener SQLite
    if not DB_PATH.exists():
        print(f"\nERROR: CourtListener database not found at {DB_PATH}")
        print("Run: python scripts/setup_bulk_data.py")
        return 1

    print(f"\nMatching against: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    to_match = cases
    if args.limit:
        to_match = cases[:args.limit]
        print(f"Limited to {args.limit} cases for testing")

    matched = 0
    exact = 0
    likely = 0
    unmatched = 0

    for i, case in enumerate(to_match):
        if (i + 1) % 500 == 0 or args.verbose:
            print(f"[{i+1}/{len(to_match)}] {case['name'][:60]}")

        result = search_local_db(
            conn, case["name"], case["citation"], verbose=args.verbose
        )

        if result:
            case["cluster_id"] = result["cluster_id"]
            case["match_confidence"] = result["confidence"]
            case["cl_case_name"] = result["case_name"]
            case["date_filed"] = result["date_filed"]
            case["citation_found"] = result["citation_found"]
            matched += 1
            if result["confidence"] == "exact":
                exact += 1
            else:
                likely += 1

            if args.verbose:
                print(f"  -> {result['confidence']}: {result['case_name']} (cluster {result['cluster_id']})")
        else:
            unmatched += 1
            if args.verbose:
                print(f"  -> NOT FOUND")

    conn.close()

    # Step 3: Print stats
    print(f"\n{'='*60}")
    print("MATCHING RESULTS")
    print(f"{'='*60}")
    print(f"Total cases:    {len(to_match)}")
    print(f"Matched:        {matched} ({100*matched/len(to_match):.1f}%)")
    print(f"  Exact:        {exact}")
    print(f"  Likely:       {likely}")
    print(f"Unmatched:      {unmatched}")
    print(f"{'='*60}")

    # Show top unmatched cases (by casebook count)
    unmatched_cases = [c for c in to_match if not c.get("cluster_id")]
    if unmatched_cases:
        print(f"\nTop unmatched cases:")
        for c in unmatched_cases[:10]:
            print(f"  [{c['casebook_count']} books] {c['name']} | {c['citation']}")

    # Step 4: Save output
    output = {
        "stats": {
            "total": len(to_match),
            "with_citations": sum(1 for c in to_match if c["citation"]),
            "matched": matched,
            "exact": exact,
            "likely": likely,
            "unmatched": unmatched,
            "match_rate": f"{100*matched/len(to_match):.1f}%"
        },
        "cases": to_match,
        "casebooks": casebooks
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
