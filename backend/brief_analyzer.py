#!/usr/bin/env python3

"""
Brief Analysis Module
Extracts citations, validates them, and provides AI-enhanced analysis
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import eyecite
from eyecite import get_citations, clean_text
from eyecite.models import FullCaseCitation, ShortCaseCitation, IdCitation
import pdfplumber
from docx import Document
import PyPDF2
import asyncpg
import openai
import os
from datetime import datetime
import hashlib

@dataclass
class Citation:
    """Represents a legal citation found in a brief"""
    text: str
    reporter: Optional[str] = None
    volume: Optional[int] = None
    page: Optional[int] = None
    year: Optional[int] = None
    case_name: Optional[str] = None
    court: Optional[str] = None
    location_in_brief: Optional[int] = None
    confidence: float = 1.0

@dataclass
class BriefAnalysis:
    """Complete analysis of a legal brief"""
    total_citations: int
    extracted_citations: List[Citation]
    validated_citations: List[Dict]
    missing_authorities: List[Dict]
    problematic_citations: List[Dict]
    suggested_cases: List[Dict]
    key_arguments: List[str]
    ai_summary: Optional[str] = None
    analysis_cost: float = 0.0

class BriefAnalyzer:
    """Analyzes legal briefs for citations and arguments"""

    def __init__(self, database_url: str, openai_api_key: Optional[str] = None):
        self.database_url = database_url
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
            openai.api_key = self.openai_api_key

    async def analyze_brief(self, file_content: bytes, filename: str,
                           use_ai: bool = True) -> BriefAnalysis:
        """Main entry point for brief analysis"""

        # Step 1: Extract text from document
        text = self.extract_text(file_content, filename)

        # Step 2: Extract citations using Eyecite
        citations = self.extract_citations(text)

        # Step 3: Validate citations against database
        validated, problematic = await self.validate_citations(citations)

        # Step 4: Find missing authorities
        missing = await self.find_missing_authorities(text, citations)

        # Step 5: Extract key arguments
        key_arguments = self.extract_key_arguments(text)

        # Step 6: AI analysis (if enabled and API key available)
        suggested_cases = []
        ai_summary = None
        cost = 0.0

        if use_ai and self.openai_api_key and key_arguments:
            suggested_cases, ai_cost = await self.find_similar_cases_ai(key_arguments)
            ai_summary, summary_cost = await self.generate_ai_summary(
                text[:3000], citations, key_arguments
            )
            cost = ai_cost + summary_cost

        return BriefAnalysis(
            total_citations=len(citations),
            extracted_citations=citations,
            validated_citations=validated,
            missing_authorities=missing,
            problematic_citations=problematic,
            suggested_cases=suggested_cases,
            key_arguments=key_arguments,
            ai_summary=ai_summary,
            analysis_cost=cost
        )

    def extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF or DOCX file"""

        if filename.lower().endswith('.pdf'):
            return self.extract_pdf_text(file_content)
        elif filename.lower().endswith('.docx'):
            return self.extract_docx_text(file_content)
        else:
            # Try to decode as plain text
            try:
                return file_content.decode('utf-8')
            except:
                return file_content.decode('latin-1')

    def extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF"""
        try:
            # Try pdfplumber first (better for complex PDFs)
            import io
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        except:
            # Fallback to PyPDF2
            try:
                import io
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except:
                return ""

    def extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX"""
        try:
            import io
            doc = Document(io.BytesIO(content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except:
            return ""

    def extract_citations(self, text: str) -> List[Citation]:
        """Extract legal citations using Eyecite"""

        # Clean the text for better citation extraction
        cleaned = clean_text(text, ['all_whitespace'])

        # Get citations using Eyecite
        raw_citations = get_citations(cleaned)

        citations = []
        for cite in raw_citations:
            # Extract clean citation text
            if hasattr(cite, 'matched_text'):
                citation_text = cite.matched_text
            else:
                citation_text = str(cite).split("'")[1] if "'" in str(cite) else str(cite)

            citation = Citation(
                text=citation_text,
                location_in_brief=cite.index if hasattr(cite, 'index') else None
            )

            # Extract details based on citation type
            if isinstance(cite, FullCaseCitation):
                # Extract from groups dictionary
                if hasattr(cite, 'groups'):
                    citation.reporter = cite.groups.get('reporter', '')
                    citation.volume = int(cite.groups.get('volume')) if cite.groups.get('volume') else None
                    citation.page = int(cite.groups.get('page')) if cite.groups.get('page') else None

                # Extract metadata
                if hasattr(cite, 'metadata') and cite.metadata:
                    citation.year = int(cite.metadata.year) if cite.metadata.year else None
                    citation.court = cite.metadata.court if hasattr(cite.metadata, 'court') else None

                    # Build case name from plaintiff v. defendant
                    if hasattr(cite.metadata, 'plaintiff') and cite.metadata.plaintiff:
                        case_name = cite.metadata.plaintiff
                        if hasattr(cite.metadata, 'defendant') and cite.metadata.defendant:
                            case_name += f" v. {cite.metadata.defendant}"
                        citation.case_name = case_name

                # Build clean citation text if we have components
                if citation.volume and citation.reporter and citation.page:
                    formatted_text = f"{citation.volume} {citation.reporter} {citation.page}"
                    if citation.year:
                        formatted_text += f" ({citation.year})"
                    if citation.case_name:
                        formatted_text = f"{citation.case_name}, {formatted_text}"
                    citation.text = formatted_text

            citations.append(citation)

        # Also look for common patterns Eyecite might miss
        additional = self.extract_additional_citations(text)
        citations.extend(additional)

        return citations

    def extract_additional_citations(self, text: str) -> List[Citation]:
        """Extract citations that Eyecite might miss"""

        citations = []

        # Pattern for "See [Case Name], [Citation]"
        see_pattern = r'See\s+([A-Z][^,]+?),\s+(\d+\s+[A-Z]\.\d+\s+\d+)'
        for match in re.finditer(see_pattern, text):
            citations.append(Citation(
                text=match.group(0),
                case_name=match.group(1).strip(),
                confidence=0.8
            ))

        # Pattern for "Id. at [page]" references
        id_pattern = r'Id\.\s+at\s+\d+'
        for match in re.finditer(id_pattern, text):
            citations.append(Citation(
                text=match.group(0),
                confidence=0.6
            ))

        return citations

    async def validate_citations(self, citations: List[Citation]) -> Tuple[List[Dict], List[Dict]]:
        """Validate citations against database"""

        validated = []
        problematic = []

        conn = await asyncpg.connect(self.database_url)

        try:
            for cite in citations:
                # Try to find in database
                found = False
                problem = None

                # Try multiple search strategies
                row = None

                # First, try to match by case name if available
                if cite.case_name:
                    query = """
                        SELECT id, case_name, date_filed, citation_count
                        FROM cases
                        WHERE case_name ILIKE $1
                        LIMIT 1
                    """
                    row = await conn.fetchrow(query, f"%{cite.case_name}%")

                # If not found and we have citation components, search by citation
                if not row and cite.volume and cite.reporter and cite.page:
                    citation_pattern = f"%{cite.volume}%{cite.reporter}%{cite.page}%"
                    query = """
                        SELECT id, case_name, date_filed, citation_count
                        FROM cases
                        WHERE metadata::text ILIKE $1 OR content ILIKE $1
                        LIMIT 1
                    """
                    row = await conn.fetchrow(query, citation_pattern)

                # Finally, try partial text search
                if not row and cite.text and isinstance(cite.text, str):
                    # Extract just the case name part if it's a full citation
                    if " v. " in cite.text:
                        case_name_part = cite.text.split(",")[0] if "," in cite.text else cite.text
                        query = """
                            SELECT id, case_name, date_filed, citation_count
                            FROM cases
                            WHERE case_name ILIKE $1
                            LIMIT 1
                        """
                        row = await conn.fetchrow(query, f"%{case_name_part}%")

                if row:
                    validated.append({
                        "citation": asdict(cite),
                        "found_case": dict(row),
                        "status": "valid"
                    })
                    found = True

                if not found:
                    # Check if it might be problematic
                    if cite.year and cite.year < 1950:
                        problem = "Very old case - check if still good law"
                    elif cite.text and isinstance(cite.text, str) and "overruled" in cite.text.lower():
                        problem = "May have been overruled"
                    elif not cite.reporter:
                        problem = "Incomplete citation format"

                    problematic.append({
                        "citation": asdict(cite),
                        "problem": problem or "Not found in database",
                        "status": "warning"
                    })

        finally:
            await conn.close()

        return validated, problematic

    async def find_missing_authorities(self, text: str, citations: List[Citation]) -> List[Dict]:
        """Find important cases that should have been cited"""

        missing = []

        # Detect legal areas discussed
        legal_areas = self.detect_legal_areas(text)

        conn = await asyncpg.connect(self.database_url)

        try:
            # Foundation cases for each area
            foundation_cases = {
                "personal jurisdiction": ["International Shoe", "World-Wide Volkswagen"],
                "due process": ["Mathews v. Eldridge", "Goldberg v. Kelly"],
                "summary judgment": ["Celotex", "Anderson v. Liberty Lobby"],
                "qualified immunity": ["Harlow v. Fitzgerald", "Pearson v. Callahan"],
                "class action": ["Wal-Mart v. Dukes", "Comcast v. Behrend"]
            }

            cited_case_names = []
            for c in citations:
                if c.case_name and isinstance(c.case_name, str):
                    cited_case_names.append(c.case_name)
                elif c.text and isinstance(c.text, str):
                    cited_case_names.append(c.text)

            for area in legal_areas:
                if area in foundation_cases:
                    for case_name in foundation_cases[area]:
                        # Check if already cited
                        if not any(case_name.lower() in cited.lower() for cited in cited_case_names if isinstance(cited, str)):
                            # Try to find in database
                            query = """
                                SELECT id, case_name, date_filed, citation_count
                                FROM cases
                                WHERE case_name ILIKE $1
                                ORDER BY citation_count DESC
                                LIMIT 1
                            """

                            row = await conn.fetchrow(query, f"%{case_name}%")

                            if row:
                                missing.append({
                                    "case": dict(row),
                                    "reason": f"Foundation case for {area}",
                                    "importance": "high"
                                })

        finally:
            await conn.close()

        return missing

    def detect_legal_areas(self, text: str) -> List[str]:
        """Detect legal areas discussed in the brief"""

        areas = []
        text_lower = text.lower()

        area_keywords = {
            "personal jurisdiction": ["personal jurisdiction", "minimum contacts", "purposeful availment"],
            "due process": ["due process", "procedural due process", "substantive due process"],
            "summary judgment": ["summary judgment", "genuine issue", "material fact"],
            "qualified immunity": ["qualified immunity", "clearly established", "constitutional violation"],
            "class action": ["class action", "commonality", "typicality", "numerosity"]
        }

        for area, keywords in area_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                areas.append(area)

        return areas

    def extract_key_arguments(self, text: str, max_arguments: int = 5) -> List[str]:
        """Extract key legal arguments from the brief"""

        arguments = []

        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)

        # Look for argument indicators
        argument_patterns = [
            r'argue[sd]?\s+that',
            r'contend[sd]?\s+that',
            r'maintain[sd]?\s+that',
            r'submit[sd]?\s+that',
            r'assert[sd]?\s+that',
            r'position\s+is\s+that',
            r'claim[sd]?\s+that',
            r'respectfully\s+submit',
        ]

        for sentence in sentences:
            for pattern in argument_patterns:
                if re.search(pattern, sentence.lower()):
                    # Clean and add the argument
                    clean_arg = sentence.strip()
                    if len(clean_arg) > 50 and len(clean_arg) < 500:
                        arguments.append(clean_arg)
                        break

            if len(arguments) >= max_arguments:
                break

        return arguments

    async def find_similar_cases_ai(self, arguments: List[str]) -> Tuple[List[Dict], float]:
        """Use AI to find similar cases based on arguments"""

        if not self.openai_api_key or not arguments:
            return [], 0.0

        suggested = []
        total_cost = 0.0

        conn = await asyncpg.connect(self.database_url)

        try:
            # Generate embedding for key arguments (Phase 2)
            for arg in arguments[:3]:  # Limit to 3 to control costs
                # Generate embedding
                response = openai.embeddings.create(
                    input=arg[:8000],
                    model="text-embedding-3-small"
                )

                embedding = response.data[0].embedding
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'

                # Calculate embedding cost ($0.02 per 1M tokens for text-embedding-3-small)
                tokens = len(arg) / 4  # Rough estimate
                total_cost += (tokens / 1_000_000) * 0.02

                # Find similar cases
                query = """
                    SELECT id, case_name, date_filed, citation_count,
                           1 - (embedding <=> $1::vector) as similarity
                    FROM cases
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT 3
                """

                rows = await conn.fetch(query, embedding_str)

                for row in rows:
                    if row['similarity'] > 0.7:  # Only highly similar
                        suggested.append({
                            "case": dict(row),
                            "argument_matched": arg[:100] + "...",
                            "similarity": float(row['similarity']),
                            "relevance": "high" if row['similarity'] > 0.8 else "medium"
                        })

        finally:
            await conn.close()

        # Remove duplicates
        seen = set()
        unique = []
        for item in suggested:
            case_id = item['case']['id']
            if case_id not in seen:
                seen.add(case_id)
                unique.append(item)

        return unique[:10], total_cost

    async def generate_ai_summary(self, text_sample: str, citations: List[Citation],
                                 arguments: List[str]) -> Tuple[Optional[str], float]:
        """Generate AI summary of the brief analysis"""

        if not self.openai_api_key:
            return None, 0.0

        # Prepare context
        context = f"""
        Brief excerpt: {text_sample[:1500]}

        Number of citations found: {len(citations)}
        Key arguments identified: {len(arguments)}
        First argument: {arguments[0] if arguments else 'None identified'}
        """

        try:
            # Use GPT-5-mini for enhanced legal analysis
            response = openai.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=[
                    {"role": "system", "content": "You are an expert legal analyst providing clear, comprehensive case summaries for lawyers."},
                    {"role": "user", "content": f"""
                    Please provide a comprehensive summary of this legal brief in plain English:

                    📖 CASE SUMMARY
                    Write a clear 3-4 paragraph summary explaining:
                    - What this case is about
                    - Who the parties are and what happened
                    - What legal issues are being argued
                    - What the party is asking the court to do

                    ⚖️ MAIN ARGUMENTS
                    - Summarize the key legal arguments being made
                    - Explain the legal theories being relied upon

                    📚 IMPORTANT CASES CITED
                    - List the most significant cases referenced
                    - Briefly explain why each case supports the argument

                    🎯 BOTTOM LINE
                    - What is the core dispute?
                    - What outcome is being sought?

                    Write in a clear, professional tone that a lawyer or client could easily understand.
                    Avoid legal jargon where possible and explain technical terms when used.

                    Context: {context}

                    Key arguments from brief: {', '.join(arguments[:3]) if arguments else 'None identified'}
                    Valid citations found: {len([c for c in citations if c.case_name])} cases verified in database
                    """}
                ],
                max_completion_tokens=500,
                temperature=1
            )

            summary = response.choices[0].message.content

            # Calculate cost for GPT-5-mini ($2/1M input, $8/1M output tokens)
            input_tokens = len(context) / 4  # Rough estimate
            output_tokens = 500  # Max output tokens
            cost = (input_tokens / 1_000_000) * 2.00 + (output_tokens / 1_000_000) * 8.00

            return summary, cost

        except Exception as e:
            print(f"AI summary error: {e}")
            return None, 0.0

# Standalone function for testing
async def test_analyzer():
    """Test the brief analyzer with sample text"""

    analyzer = BriefAnalyzer(
        database_url="postgresql://legal_user:legal_pass@localhost:5432/legal_research"
    )

    sample_brief = """
    ARGUMENT

    I. THE DISTRICT COURT LACKS PERSONAL JURISDICTION

    Plaintiff argues that this Court has personal jurisdiction over Defendant based on
    minimum contacts. See International Shoe Co. v. Washington, 326 U.S. 310 (1945).
    However, as established in World-Wide Volkswagen Corp. v. Woodson, 444 U.S. 286 (1980),
    mere foreseeability is insufficient to establish personal jurisdiction.

    The Defendant contends that it lacks sufficient contacts with the forum state.
    The Supreme Court's recent decision in Ford Motor Co. v. Montana, 141 S. Ct. 1017 (2021)
    does not change this analysis.

    II. SUMMARY JUDGMENT IS APPROPRIATE

    Under Fed. R. Civ. P. 56, summary judgment is appropriate when there is no genuine
    issue of material fact. See Celotex Corp. v. Catrett, 477 U.S. 317 (1986).
    """

    # Convert to bytes (simulating file upload)
    content = sample_brief.encode('utf-8')

    # Analyze
    result = await analyzer.analyze_brief(content, "test_brief.txt", use_ai=False)

    print(f"Found {result.total_citations} citations")
    print(f"Validated: {len(result.validated_citations)}")
    print(f"Problematic: {len(result.problematic_citations)}")
    print(f"Missing authorities: {len(result.missing_authorities)}")
    print(f"Key arguments: {len(result.key_arguments)}")

    return result

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_analyzer())