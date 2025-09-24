import asyncio
import asyncpg
import httpx
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import hashlib
from opensearchpy import AsyncOpenSearch
import logging
import eyecite
from eyecite import get_citations, resolve_citations, clean_text
from eyecite.models import CaseCitation
import pdfplumber
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
COURTLISTENER_API_KEY = os.getenv("COURTLISTENER_API_KEY")

class LegalETLPipeline:
    def __init__(self):
        self.db_pool = None
        self.osearch_client = None
        self.processed_count = 0
        self.error_count = 0

    async def initialize(self):
        """Initialize database and search connections"""
        self.db_pool = await asyncpg.create_pool(DATABASE_URL)
        self.osearch_client = AsyncOpenSearch(hosts=[OPENSEARCH_URL])
        
        # Create tables if not exist
        await self.create_tables()
        
        logger.info("ETL Pipeline initialized")

    async def create_tables(self):
        """Create necessary database tables"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                
                CREATE TABLE IF NOT EXISTS courts (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    jurisdiction TEXT,
                    level TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    court_id INTEGER REFERENCES courts(id),
                    title TEXT NOT NULL,
                    docket_number TEXT,
                    decision_date DATE,
                    reporter_cite TEXT,
                    neutral_cite TEXT,
                    precedential BOOLEAN DEFAULT TRUE,
                    content TEXT,
                    content_hash TEXT,
                    embedding vector(1536),
                    metadata JSONB,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS case_chunks (
                    id SERIAL PRIMARY KEY,
                    case_id TEXT REFERENCES cases(id),
                    chunk_index INTEGER,
                    section TEXT,
                    content TEXT,
                    embedding vector(1536),
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS citations (
                    id SERIAL PRIMARY KEY,
                    source_case_id TEXT REFERENCES cases(id),
                    target_case_id TEXT REFERENCES cases(id),
                    context_span TEXT,
                    signal TEXT,
                    paragraph_num INTEGER,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS etl_jobs (
                    id SERIAL PRIMARY KEY,
                    job_type TEXT,
                    status TEXT,
                    started_at TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP,
                    records_processed INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    metadata JSONB
                );
                
                CREATE INDEX IF NOT EXISTS idx_cases_date ON cases(decision_date);
                CREATE INDEX IF NOT EXISTS idx_cases_court ON cases(court_id);
                CREATE INDEX IF NOT EXISTS idx_citations_source ON citations(source_case_id);
                CREATE INDEX IF NOT EXISTS idx_citations_target ON citations(target_case_id);
                CREATE INDEX IF NOT EXISTS idx_cases_embedding ON cases 
                    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON case_chunks 
                    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
            """)
            logger.info("Database tables created/verified")

    async def fetch_courtlistener_bulk(self, court="scotus", limit=100):
        """Fetch cases from CourtListener API"""

        job_id = await self.start_job("courtlistener_import", {"court": court})

        try:
            async with httpx.AsyncClient() as client:
                # Fetch opinions using v4 API
                response = await client.get(
                    "https://www.courtlistener.com/api/rest/v4/opinions/",
                    params={
                        "cluster__docket__court__id": court,
                        "order_by": "-cluster__date_filed",
                        "page_size": limit
                    },
                    headers={"Authorization": f"Token {COURTLISTENER_API_KEY}"} if COURTLISTENER_API_KEY else {}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    cases = data.get("results", [])
                    
                    for case_data in cases:
                        await self.process_case(case_data)
                        self.processed_count += 1
                    
                    logger.info(f"Processed {self.processed_count} cases from {court}")
                else:
                    logger.error(f"Failed to fetch data: {response.status_code}")
                    self.error_count += 1
        
        except Exception as e:
            logger.error(f"ETL error: {e}")
            self.error_count += 1
        
        finally:
            await self.complete_job(job_id, self.processed_count, self.error_count)

    async def process_case(self, case_data: Dict[str, Any]):
        """Process a single case"""
        
        try:
            # Extract basic metadata
            case_id = case_data.get("id", "")
            if not case_id:
                case_id = hashlib.md5(
                    f"{case_data.get('case_name', '')}_{case_data.get('date_filed', '')}".encode()
                ).hexdigest()
            
            # Check if already processed
            async with self.db_pool.acquire() as conn:
                existing = await conn.fetchrow(
                    "SELECT id FROM cases WHERE id = $1", case_id
                )
                if existing:
                    logger.info(f"Case {case_id} already processed, skipping")
                    return
            
            # Extract text content
            content = await self.extract_case_text(case_data)
            
            # Clean and normalize text
            cleaned_content = clean_text(content, ["all_whitespace", "underscores"])
            
            # Extract citations
            citations = get_citations(cleaned_content)
            
            # Chunk the content
            chunks = self.chunk_text(cleaned_content)
            
            # Generate embeddings
            content_embedding = await self.generate_embedding(cleaned_content[:8000])  # Limit for embedding
            
            # Store in database
            async with self.db_pool.acquire() as conn:
                # Get or create court
                court_id = await self.get_or_create_court(conn, case_data.get("court", {}))
                
                # Insert case
                await conn.execute("""
                    INSERT INTO cases (
                        id, court_id, title, docket_number, decision_date,
                        reporter_cite, content, content_hash, embedding,
                        metadata, source_url
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector, $10, $11)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                """, 
                    case_id,
                    court_id,
                    case_data.get("case_name", "Unknown"),
                    case_data.get("docket_number"),
                    datetime.fromisoformat(case_data.get("date_filed", "1900-01-01")),
                    case_data.get("citation"),
                    cleaned_content,
                    hashlib.sha256(cleaned_content.encode()).hexdigest(),
                    content_embedding,
                    json.dumps(case_data),
                    case_data.get("absolute_url")
                )
                
                # Insert chunks with embeddings
                for i, chunk in enumerate(chunks):
                    chunk_embedding = await self.generate_embedding(chunk["text"])
                    await conn.execute("""
                        INSERT INTO case_chunks (
                            case_id, chunk_index, section, content, embedding
                        ) VALUES ($1, $2, $3, $4, $5::vector)
                    """,
                        case_id, i, chunk["section"], chunk["text"], chunk_embedding
                    )
                
                # Process citations
                for citation in citations:
                    if isinstance(citation, CaseCitation):
                        await self.process_citation(conn, case_id, citation)
            
            # Index in OpenSearch
            await self.index_to_opensearch(case_id, case_data, cleaned_content, chunks)
            
            logger.info(f"Successfully processed case {case_id}")
            
        except Exception as e:
            logger.error(f"Error processing case: {e}")
            self.error_count += 1

    async def extract_case_text(self, case_data: Dict) -> str:
        """Extract text from various sources"""
        
        # Try HTML content first
        if "html_lawbox" in case_data:
            soup = BeautifulSoup(case_data["html_lawbox"], "html.parser")
            return soup.get_text()
        
        # Try plain text
        if "plain_text" in case_data:
            return case_data["plain_text"]
        
        # Try PDF URL
        if "download_url" in case_data:
            return await self.extract_pdf_text(case_data["download_url"])
        
        return case_data.get("text", "")

    async def extract_pdf_text(self, pdf_url: str) -> str:
        """Download and extract text from PDF"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(pdf_url)
                if response.status_code == 200:
                    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                        text = ""
                        for page in pdf.pages:
                            text += page.extract_text() or ""
                        return text
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
        return ""

    def chunk_text(self, text: str, chunk_size=1000, overlap=200) -> List[Dict]:
        """Chunk text into overlapping segments"""
        
        chunks = []
        
        # Split by sections if identifiable
        sections = self.identify_sections(text)
        
        for section_name, section_text in sections.items():
            # Split long sections into chunks
            words = section_text.split()
            
            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                chunks.append({
                    "section": section_name,
                    "text": chunk_text,
                    "start_pos": i,
                    "end_pos": min(i + chunk_size, len(words))
                })
        
        return chunks

    def identify_sections(self, text: str) -> Dict[str, str]:
        """Identify major sections in legal opinion"""
        
        sections = {"full_text": text}
        
        # Common section markers
        markers = [
            ("SYLLABUS", "syllabus"),
            ("OPINION", "majority"),
            ("CONCUR", "concurrence"),
            ("DISSENT", "dissent"),
            ("BACKGROUND", "background"),
            ("DISCUSSION", "discussion"),
            ("CONCLUSION", "conclusion")
        ]
        
        for marker, section_name in markers:
            if marker in text.upper():
                # Extract section (simplified)
                start = text.upper().find(marker)
                # Find next section or end
                end = len(text)
                for next_marker, _ in markers:
                    next_pos = text.upper().find(next_marker, start + len(marker))
                    if next_pos > 0 and next_pos < end:
                        end = next_pos
                
                sections[section_name] = text[start:end]
        
        return sections

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI API"""
        
        if not OPENAI_API_KEY:
            # Return random embedding for testing
            import random
            return [random.random() for _ in range(1536)]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "input": text[:8000],  # Limit tokens
                        "model": "text-embedding-3-small"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
        
        # Return zero embedding on error
        return [0.0] * 1536

    async def index_to_opensearch(self, case_id: str, case_data: Dict, 
                                   content: str, chunks: List[Dict]):
        """Index case in OpenSearch for BM25 search"""
        
        try:
            # Index main document
            await self.osearch_client.index(
                index="cases",
                id=case_id,
                body={
                    "case_id": case_id,
                    "title": case_data.get("case_name", ""),
                    "court": case_data.get("court", {}).get("name", ""),
                    "date": case_data.get("date_filed"),
                    "content": content,
                    "docket_number": case_data.get("docket_number"),
                    "reporter_cite": case_data.get("citation"),
                    "jurisdiction": case_data.get("court", {}).get("jurisdiction", "")
                }
            )
            
            # Index chunks for granular search
            for i, chunk in enumerate(chunks):
                await self.osearch_client.index(
                    index="case_chunks",
                    id=f"{case_id}_{i}",
                    body={
                        "case_id": case_id,
                        "chunk_index": i,
                        "section": chunk["section"],
                        "content": chunk["text"],
                        "date": case_data.get("date_filed")
                    }
                )
            
        except Exception as e:
            logger.error(f"Error indexing to OpenSearch: {e}")

    async def get_or_create_court(self, conn, court_data: Dict) -> int:
        """Get or create court record"""
        
        court_name = court_data.get("name", "Unknown Court")
        
        # Check if exists
        row = await conn.fetchrow(
            "SELECT id FROM courts WHERE name = $1", court_name
        )
        
        if row:
            return row["id"]
        
        # Create new
        row = await conn.fetchrow("""
            INSERT INTO courts (name, jurisdiction, level)
            VALUES ($1, $2, $3)
            RETURNING id
        """,
            court_name,
            court_data.get("jurisdiction", ""),
            court_data.get("level", "")
        )
        
        return row["id"]

    async def process_citation(self, conn, source_case_id: str, citation):
        """Process and store a citation"""
        
        try:
            # Try to resolve the citation to a case ID
            target_case_id = await self.resolve_citation(citation)
            
            if target_case_id:
                await conn.execute("""
                    INSERT INTO citations (
                        source_case_id, target_case_id, context_span, signal
                    ) VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                """,
                    source_case_id,
                    target_case_id,
                    str(citation),
                    self.detect_signal(citation)
                )
        except Exception as e:
            logger.error(f"Error processing citation: {e}")

    async def resolve_citation(self, citation) -> str:
        """Resolve a citation to a case ID"""
        # This would query CourtListener or local DB to find the case
        # Simplified for demo
        return None

    def detect_signal(self, citation) -> str:
        """Detect the signal/treatment of a citation"""
        # Simplified signal detection
        text = str(citation).lower()
        
        if "overrul" in text:
            return "overruled"
        elif "distinguish" in text:
            return "distinguished"
        elif "follow" in text:
            return "followed"
        elif "criticiz" in text:
            return "criticized"
        else:
            return "cited"

    async def start_job(self, job_type: str, metadata: Dict) -> int:
        """Record start of ETL job"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO etl_jobs (job_type, status, metadata)
                VALUES ($1, 'running', $2)
                RETURNING id
            """, job_type, json.dumps(metadata))
            return row["id"]

    async def complete_job(self, job_id: int, processed: int, errors: int):
        """Record completion of ETL job"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE etl_jobs
                SET status = 'completed',
                    completed_at = NOW(),
                    records_processed = $2,
                    error_count = $3
                WHERE id = $1
            """, job_id, processed, errors)

    async def cleanup(self):
        """Cleanup connections"""
        if self.db_pool:
            await self.db_pool.close()
        if self.osearch_client:
            await self.osearch_client.close()

async def main():
    """Main ETL execution"""
    pipeline = LegalETLPipeline()
    
    try:
        await pipeline.initialize()
        
        # Fetch and process cases
        courts = ["scotus", "ca9", "ca2", "cafc"]  # Start with key federal courts
        
        for court in courts:
            logger.info(f"Processing court: {court}")
            await pipeline.fetch_courtlistener_bulk(court, limit=50)
        
        logger.info(f"ETL completed. Processed: {pipeline.processed_count}, Errors: {pipeline.error_count}")
        
    finally:
        await pipeline.cleanup()

if __name__ == "__main__":
    asyncio.run(main())