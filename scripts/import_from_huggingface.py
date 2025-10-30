#!/usr/bin/env python3
"""
Import Ohio cases from Caselaw Access Project on Hugging Face

This script downloads and imports Ohio cases from the cleaned and processed
CAP dataset available on Hugging Face.

Dataset: https://huggingface.co/datasets/free-law/Caselaw_Access_Project
"""

import asyncio
import asyncpg
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from datasets import load_dataset
import re

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")

def extract_year_from_date(date_str):
    """Extract year from various date formats"""
    if not date_str:
        return None
    try:
        # Try to match year patterns
        year_match = re.search(r'\b(1[7-9]\d{2}|20\d{2})\b', str(date_str))
        if year_match:
            return int(year_match.group(1))
    except:
        pass
    return None

async def import_ohio_cases():
    """Import Ohio cases from Hugging Face CAP dataset"""

    print("="*80)
    print("🏛️  OHIO LEGAL RESEARCH - HUGGING FACE IMPORT")
    print("="*80)
    print("\nImporting Ohio cases from Caselaw Access Project")
    print("Source: https://huggingface.co/datasets/free-law/Caselaw_Access_Project\n")

    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)

    # Get Ohio court IDs
    ohio_courts = await conn.fetch("""
        SELECT id, court_listener_id, name
        FROM courts
        WHERE court_listener_id IN ('ohio', 'ohioctapp', 'ohioctcl')
    """)

    court_map = {
        'ohio': None,
        'ohioctapp': None,
        'ohioctcl': None
    }

    for court in ohio_courts:
        court_map[court['court_listener_id']] = court['id']

    print(f"📊 Ohio courts in database:")
    for cl_id, db_id in court_map.items():
        status = f"✓ (id={db_id})" if db_id else "✗ Not found"
        print(f"  {cl_id:15} {status}")
    print()

    try:
        print("📥 Loading Caselaw Access Project dataset from Hugging Face...")
        print("   (This may take a few minutes on first download)\n")

        # Load the dataset - streaming mode to handle large data
        dataset = load_dataset(
            "free-law/Caselaw_Access_Project",
            split="train",
            streaming=True
        )

        print("✓ Dataset loaded in streaming mode\n")
        print("🔍 Filtering for Ohio cases...\n")

        imported = 0
        skipped = 0
        errors = 0
        target = 10000  # Target number of cases to import

        # Process cases
        for i, case in enumerate(dataset):
            if imported >= target:
                print(f"\n✓ Reached target of {target:,} cases")
                break

            # Show progress every 100 cases processed
            if (i + 1) % 100 == 0:
                print(f"  Processed {i+1:,} cases... (imported: {imported:,}, skipped: {skipped:,}, errors: {errors})")

            try:
                # Check if this is an Ohio case
                jurisdiction = case.get('jurisdiction', '')
                court_name = case.get('court', {}).get('name', '')

                # Look for Ohio indicators
                is_ohio = False
                court_id = None

                if 'ohio' in jurisdiction.lower() or 'ohio' in court_name.lower():
                    is_ohio = True

                    # Try to map to our court
                    if 'supreme' in court_name.lower():
                        court_id = court_map['ohio']
                    elif 'appeal' in court_name.lower():
                        court_id = court_map['ohioctapp']
                    elif 'claims' in court_name.lower():
                        court_id = court_map['ohioctcl']
                    else:
                        court_id = court_map['ohio']  # Default to supreme court

                if not is_ohio:
                    skipped += 1
                    continue

                # Extract case data
                case_id = str(case.get('id', ''))
                if not case_id:
                    skipped += 1
                    continue

                # Check if already exists
                exists = await conn.fetchval(
                    "SELECT 1 FROM cases WHERE id = $1",
                    case_id
                )

                if exists:
                    skipped += 1
                    continue

                # Extract fields
                name = case.get('name', 'Unknown Case')
                date_str = case.get('decision_date', '')

                # Parse date
                decision_date = None
                if date_str:
                    try:
                        decision_date = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                    except:
                        # Try to extract year at least
                        year = extract_year_from_date(date_str)
                        if year:
                            try:
                                decision_date = datetime(year, 1, 1)
                            except:
                                pass

                # Get text content
                opinions = case.get('casebody', {}).get('data', {}).get('opinions', [])
                content = ""
                if opinions:
                    for opinion in opinions:
                        opinion_text = opinion.get('text', '')
                        if opinion_text:
                            content += opinion_text + "\n\n"

                # If no opinion text, try other fields
                if not content:
                    content = case.get('preview', '') or case.get('name', '')

                content = content[:100000]  # Limit to 100KB

                # Citations
                citations = case.get('citations', [])
                citation_str = ', '.join([c.get('cite', '') for c in citations if c.get('cite')])

                # Get first reporter cite
                reporter_cite = None
                if citations:
                    reporter_cite = citations[0].get('cite', '')

                # Import into database
                await conn.execute("""
                    INSERT INTO cases (
                        id, title, court_id, decision_date,
                        reporter_cite, content, metadata, source_url
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO NOTHING
                """,
                    case_id,
                    name[:200],
                    court_id,
                    decision_date,
                    reporter_cite,
                    content,
                    json.dumps({
                        'jurisdiction': jurisdiction,
                        'court': court_name,
                        'citations': citation_str,
                        'volume': case.get('volume', {}).get('volume_number', ''),
                        'import_source': 'huggingface_cap'
                    }),
                    case.get('url', '')
                )

                imported += 1

            except Exception as e:
                errors += 1
                if errors <= 10:  # Only show first 10 errors
                    print(f"\n  ❌ Error importing case: {e}")

        print(f"\n{'='*80}")
        print("📈 IMPORT SUMMARY")
        print(f"{'='*80}")
        print(f"  Total cases processed: {i+1:,}")
        print(f"  Ohio cases imported:   {imported:,}")
        print(f"  Cases skipped:         {skipped:,}")
        print(f"  Errors:                {errors}")

        # Get final database stats
        total_cases = await conn.fetchval("SELECT COUNT(*) FROM cases")
        ohio_cases = await conn.fetchval("""
            SELECT COUNT(*) FROM cases c
            JOIN courts ct ON c.court_id = ct.id
            WHERE ct.court_listener_id IN ('ohio', 'ohioctapp', 'ohioctcl')
        """)

        print(f"\n  Total database size:   {total_cases:,} cases")
        print(f"  Ohio cases in DB:      {ohio_cases:,} cases")

        # Show samples
        samples = await conn.fetch("""
            SELECT c.title, ct.name as court_name, c.decision_date, c.reporter_cite
            FROM cases c
            JOIN courts ct ON c.court_id = ct.id
            WHERE ct.court_listener_id IN ('ohio', 'ohioctapp', 'ohioctcl')
            ORDER BY c.decision_date DESC NULLS LAST
            LIMIT 10
        """)

        if samples:
            print(f"\n🏛️  Sample Ohio Cases:")
            for i, row in enumerate(samples, 1):
                year = row['decision_date'].year if row['decision_date'] else 'N/A'
                cite = row['reporter_cite'] or 'No citation'
                print(f"  {i:2}. {row['title'][:50]:50} | {year} | {cite[:20]}")

        print(f"\n{'='*80}")
        print("✅ IMPORT COMPLETE!")
        print(f"{'='*80}")
        print("\nYour Ohio legal research database is ready!")
        print("\nNext steps:")
        print("  1. Test search functionality")
        print("  2. Generate embeddings for semantic search")
        print("  3. Try the brief-checking feature")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(import_ohio_cases())
