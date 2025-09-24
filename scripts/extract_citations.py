#!/usr/bin/env python3
"""
Extract and populate citation relationships between cases.
Uses Eyecite to extract citations from case text and match them to cases in our database.
"""

import asyncio
import asyncpg
import json
from datetime import datetime
import eyecite
from eyecite import get_citations, resolve_citations
from eyecite.models import FullCaseCitation
from typing import List, Dict, Any
import re

DATABASE_URL = "postgresql://legal_user:legal_pass@localhost:5432/legal_research"

class CitationExtractor:
    def __init__(self, conn):
        self.conn = conn
        self.case_lookup = {}
        self.stats = {
            "cases_processed": 0,
            "citations_found": 0,
            "citations_matched": 0,
            "citations_failed": 0
        }

    async def build_case_lookup(self):
        """Build a lookup table for matching citations to database cases"""
        print("📚 Building case lookup table...")

        cases = await self.conn.fetch("""
            SELECT id, case_name, court_id, date_filed, metadata
            FROM cases
            WHERE case_name IS NOT NULL
        """)

        for case in cases:
            # Parse metadata for citations
            metadata = {}
            if case['metadata']:
                try:
                    metadata = json.loads(case['metadata']) if isinstance(case['metadata'], str) else case['metadata']
                except:
                    pass

            # Get citation strings
            citations = metadata.get('citations', [])
            citation_str = metadata.get('citation', '')

            # Add to lookup by various formats
            case_name_normalized = self.normalize_case_name(case['case_name'])
            self.case_lookup[case_name_normalized] = case['id']

            # Add citation strings to lookup
            if citation_str and isinstance(citation_str, str):
                self.case_lookup[citation_str.lower()] = case['id']

            # Handle citations list
            if isinstance(citations, list):
                for cite in citations:
                    if cite and isinstance(cite, str):
                        self.case_lookup[cite.lower()] = case['id']
            elif isinstance(citations, str) and citations:
                self.case_lookup[citations.lower()] = case['id']

            # Try to parse reporter citations (e.g., "410 U.S. 113")
            if citation_str and isinstance(citation_str, str):
                parts = citation_str.split(';')
                for part in parts:
                    part = part.strip()
                    if part:
                        self.case_lookup[part.lower()] = case['id']

        print(f"  ✓ Built lookup with {len(self.case_lookup)} entries for {len(cases)} cases")

    def normalize_case_name(self, name: str) -> str:
        """Normalize case name for matching"""
        # Remove common variations
        name = name.lower()
        name = re.sub(r'\s+v\.?\s+', ' v ', name)  # Standardize v. or vs
        name = re.sub(r'[,\.\(\)]', '', name)  # Remove punctuation
        name = re.sub(r'\s+', ' ', name).strip()  # Normalize spaces

        # Extract just the party names for shorter version
        if ' v ' in name:
            parts = name.split(' v ')
            if len(parts) == 2:
                # Get first word of each party
                plaintiff = parts[0].split()[0] if parts[0].split() else ''
                defendant = parts[1].split()[0] if parts[1].split() else ''
                if plaintiff and defendant:
                    short_name = f"{plaintiff} v {defendant}"
                    self.case_lookup[short_name] = self.case_lookup.get(name, None)

        return name

    async def extract_citations_from_case(self, case_id: str, content: str) -> List[Dict]:
        """Extract citations from case content using Eyecite"""
        citations_found = []

        try:
            # Get citations from text
            citations = get_citations(content)

            for cite in citations:
                citation_data = {
                    "raw_cite": str(cite),
                    "matched_id": None,
                    "confidence": 0.0
                }

                # Try to match citation to a case in our database
                if isinstance(cite, FullCaseCitation):
                    # Try to match by reporter citation
                    cite_str = f"{cite.groups.get('volume', '')} {cite.groups.get('reporter', '')} {cite.groups.get('page', '')}".strip()
                    citation_data["cite_str"] = cite_str

                    # Look for match in our database
                    matched_id = self.case_lookup.get(cite_str.lower())
                    if not matched_id and hasattr(cite, 'metadata') and cite.metadata:
                        # Try matching by case name
                        case_name = cite.metadata.get('case_name', '')
                        if case_name:
                            normalized = self.normalize_case_name(case_name)
                            matched_id = self.case_lookup.get(normalized)

                    if matched_id and matched_id != case_id:  # Don't self-cite
                        citation_data["matched_id"] = matched_id
                        citation_data["confidence"] = 0.9
                        citations_found.append(citation_data)

        except Exception as e:
            print(f"    ⚠️  Error extracting citations: {e}")

        return citations_found

    async def process_case(self, case_id: str, case_name: str, content: str):
        """Process a single case to extract and store citations"""
        if not content or len(content) < 100:
            return

        print(f"  📄 Processing: {case_name[:50]}...")

        # Extract citations
        citations = await self.extract_citations_from_case(case_id, content)
        self.stats["citations_found"] += len(citations)

        # Store citations in database
        for cite in citations:
            if cite["matched_id"]:
                try:
                    # Insert citation relationship
                    await self.conn.execute("""
                        INSERT INTO citations (
                            citing_case_id, cited_case_id,
                            citation_text, confidence,
                            created_at
                        ) VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (citing_case_id, cited_case_id)
                        DO UPDATE SET
                            confidence = GREATEST(citations.confidence, EXCLUDED.confidence),
                            updated_at = CURRENT_TIMESTAMP
                    """,
                        case_id,
                        cite["matched_id"],
                        cite.get("cite_str", cite["raw_cite"])[:200],
                        cite["confidence"],
                        datetime.now()
                    )
                    self.stats["citations_matched"] += 1

                except Exception as e:
                    print(f"    ⚠️  Failed to insert citation: {e}")
                    self.stats["citations_failed"] += 1

        if citations:
            matched = sum(1 for c in citations if c["matched_id"])
            print(f"    ✓ Found {len(citations)} citations, matched {matched}")

        self.stats["cases_processed"] += 1

    async def update_citation_counts(self):
        """Update citation counts for all cases"""
        print("\n📊 Updating citation counts...")

        # Update cited_by_count for each case
        await self.conn.execute("""
            UPDATE cases c
            SET citation_count = sub.count
            FROM (
                SELECT cited_case_id, COUNT(*) as count
                FROM citations
                GROUP BY cited_case_id
            ) sub
            WHERE c.id = sub.cited_case_id
        """)

        # Get top cited cases
        top_cited = await self.conn.fetch("""
            SELECT c.case_name, c.citation_count
            FROM cases c
            WHERE c.citation_count > 0
            ORDER BY c.citation_count DESC
            LIMIT 10
        """)

        if top_cited:
            print("\n🏆 Top Cited Cases (from our extraction):")
            for i, row in enumerate(top_cited, 1):
                print(f"  {i:2}. {row['case_name'][:50]:50} | {row['citation_count']} citations")

async def main():
    print("=" * 60)
    print("Citation Extraction Pipeline")
    print("=" * 60)

    conn = await asyncpg.connect(DATABASE_URL)
    extractor = CitationExtractor(conn)

    try:
        # Build lookup table
        await extractor.build_case_lookup()

        # Get cases with substantial content
        cases = await conn.fetch("""
            SELECT id, case_name, content
            FROM cases
            WHERE LENGTH(content) > 1000
            ORDER BY citation_count DESC NULLS LAST
            LIMIT 100
        """)

        print(f"\n🔍 Processing {len(cases)} cases with substantial content...")

        # Process each case
        for case in cases:
            await extractor.process_case(
                case['id'],
                case['case_name'],
                case['content']
            )

        # Update citation counts
        await extractor.update_citation_counts()

        # Print summary statistics
        print("\n" + "=" * 60)
        print("📈 Extraction Summary")
        print("=" * 60)
        print(f"  Cases processed: {extractor.stats['cases_processed']}")
        print(f"  Citations found: {extractor.stats['citations_found']}")
        print(f"  Citations matched: {extractor.stats['citations_matched']}")
        print(f"  Match rate: {extractor.stats['citations_matched'] / max(extractor.stats['citations_found'], 1) * 100:.1f}%")

        # Show sample citation relationships
        sample = await conn.fetch("""
            SELECT
                citing.case_name as citing_case,
                cited.case_name as cited_case,
                cit.citation_text,
                cit.confidence
            FROM citations cit
            JOIN cases citing ON cit.citing_case_id = citing.id
            JOIN cases cited ON cit.cited_case_id = cited.id
            ORDER BY cit.confidence DESC, cit.created_at DESC
            LIMIT 5
        """)

        if sample:
            print("\n📖 Sample Citation Relationships:")
            for row in sample:
                print(f"  • {row['citing_case'][:30]:30} → {row['cited_case'][:30]:30}")
                print(f"    Citation: {row['citation_text'][:50]} (confidence: {row['confidence']:.1%})")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())