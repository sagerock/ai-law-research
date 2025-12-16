#!/usr/bin/env python3
"""
Import citation relationships between our cases from local CourtListener data.
Uses the citation-map CSV which has opinion_id relationships.
"""

import asyncio
import asyncpg
import csv
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")
CITATION_MAP_PATH = Path("/home/sage/scripts/ai-law-research/data/courtlistener/citation-map-2025-12-02.csv")

async def main():
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Get all our case IDs (these are opinion IDs)
        rows = await conn.fetch("SELECT id FROM cases")
        our_case_ids = set(row['id'] for row in rows)
        print(f"Found {len(our_case_ids)} cases in database")

        # Read citation map and find citations between our cases
        citations_found = []
        rows_processed = 0

        print(f"Scanning citation map: {CITATION_MAP_PATH}")
        print("This may take a few minutes for the 2.7GB file...")

        with open(CITATION_MAP_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows_processed += 1
                if rows_processed % 10_000_000 == 0:
                    print(f"  Processed {rows_processed:,} rows, found {len(citations_found)} matches...")

                cited_id = row['cited_opinion_id']
                citing_id = row['citing_opinion_id']

                # Check if both cases are in our database
                if cited_id in our_case_ids and citing_id in our_case_ids:
                    citations_found.append({
                        'source_case_id': citing_id,  # The case that cites
                        'target_case_id': cited_id,   # The case being cited
                        'depth': int(row['depth'])
                    })

        print(f"\nScanned {rows_processed:,} total citation records")
        print(f"Found {len(citations_found)} citations between our {len(our_case_ids)} cases")

        if not citations_found:
            print("No citations found between our cases in the citation map.")
            print("This might mean our cases cite cases outside our set, or the IDs don't match.")
            return

        # Clear existing citations
        await conn.execute("DELETE FROM citations")
        print("Cleared existing citations")

        # Insert citations
        inserted = 0
        for cit in citations_found:
            try:
                await conn.execute("""
                    INSERT INTO citations (source_case_id, target_case_id, confidence)
                    VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                """, cit['source_case_id'], cit['target_case_id'], 1.0)
                inserted += 1
            except Exception as e:
                print(f"  Error inserting citation: {e}")

        print(f"Inserted {inserted} citations into database")

        # Show some examples
        examples = await conn.fetch("""
            SELECT
                c.source_case_id,
                s.title as citing_case,
                c.target_case_id,
                t.title as cited_case
            FROM citations c
            JOIN cases s ON c.source_case_id = s.id
            JOIN cases t ON c.target_case_id = t.id
            LIMIT 10
        """)

        print("\nExample citations found:")
        for ex in examples:
            print(f"  {ex['citing_case'][:50]} -> {ex['cited_case'][:50]}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
