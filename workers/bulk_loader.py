import asyncio
import asyncpg
import pandas as pd
import numpy as np
from pathlib import Path
import bz2
import gzip
import logging
import httpx
from datetime import datetime
from typing import AsyncIterator, Dict, Any, Optional
import json
from tqdm import tqdm
import hashlib
from opensearchpy import AsyncOpenSearch
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATA_DIR = os.getenv("DATA_DIR", "./data/bulk")

# CourtListener bulk data URLs
BULK_DATA_BASE = "https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/bulk-data"

class BulkDataLoader:
    """Handles bulk data imports from CourtListener CSV files"""

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_pool = None
        self.osearch_client = None
        self.checkpoint_file = self.data_dir / "import_checkpoint.json"
        self.batch_size = 1000

    async def initialize(self):
        """Initialize database connections"""
        self.db_pool = await asyncpg.create_pool(DATABASE_URL)
        self.osearch_client = AsyncOpenSearch(hosts=[OPENSEARCH_URL])
        logger.info("Bulk loader initialized")

    async def download_file(self, filename: str, force: bool = False) -> Path:
        """Download a bulk data file if not already present"""

        local_path = self.data_dir / filename

        # Check if already downloaded
        if local_path.exists() and not force:
            logger.info(f"File {filename} already exists, skipping download")
            return local_path

        url = f"{BULK_DATA_BASE}/{filename}"
        logger.info(f"Downloading {url}")

        async with httpx.AsyncClient() as client:
            # Stream download for large files
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                # Get total size for progress bar
                total_size = int(response.headers.get("content-length", 0))

                with open(local_path, "wb") as f:
                    with tqdm(total=total_size, unit="B", unit_scale=True) as pbar:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))

        logger.info(f"Downloaded {filename}")
        return local_path

    def decompress_file(self, filepath: Path) -> Path:
        """Decompress bz2 or gz files"""

        decompressed_path = filepath.with_suffix("")

        if decompressed_path.exists():
            logger.info(f"Decompressed file already exists: {decompressed_path}")
            return decompressed_path

        logger.info(f"Decompressing {filepath}")

        if filepath.suffix == ".bz2":
            with bz2.open(filepath, "rb") as f_in:
                with open(decompressed_path, "wb") as f_out:
                    for chunk in iter(lambda: f_in.read(8192), b""):
                        f_out.write(chunk)

        elif filepath.suffix == ".gz":
            with gzip.open(filepath, "rb") as f_in:
                with open(decompressed_path, "wb") as f_out:
                    for chunk in iter(lambda: f_in.read(8192), b""):
                        f_out.write(chunk)
        else:
            return filepath

        logger.info(f"Decompressed to {decompressed_path}")
        return decompressed_path

    async def load_courts(self, filename: str = "courts.csv.bz2"):
        """Load courts data"""

        # Download and decompress
        compressed_file = await self.download_file(filename)
        csv_file = self.decompress_file(compressed_file)

        logger.info("Loading courts data")

        # Read CSV
        df = pd.read_csv(csv_file, encoding='utf-8')

        # Insert courts
        async with self.db_pool.acquire() as conn:
            for _, row in tqdm(df.iterrows(), total=len(df), desc="Loading courts"):
                await conn.execute("""
                    INSERT INTO courts (name, jurisdiction, level, abbreviation)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (name) DO UPDATE SET
                        jurisdiction = EXCLUDED.jurisdiction,
                        level = EXCLUDED.level,
                        abbreviation = EXCLUDED.abbreviation
                """,
                    row.get('name', ''),
                    row.get('jurisdiction', ''),
                    row.get('level', ''),
                    row.get('abbreviation', '')
                )

        logger.info(f"Loaded {len(df)} courts")

    async def load_opinions_chunked(self, filename: str = "opinions.csv.bz2"):
        """Load opinions data in chunks to handle large files"""

        # Download and decompress
        compressed_file = await self.download_file(filename)
        csv_file = self.decompress_file(compressed_file)

        # Load checkpoint if exists
        checkpoint = self.load_checkpoint()
        start_row = checkpoint.get('opinions_row', 0)

        logger.info(f"Loading opinions from row {start_row}")

        # Process in chunks
        chunk_size = 1000
        total_processed = start_row

        for chunk in pd.read_csv(csv_file, chunksize=chunk_size,
                                  skiprows=range(1, start_row + 1) if start_row > 0 else None):

            await self.process_opinion_chunk(chunk)
            total_processed += len(chunk)

            # Update checkpoint
            self.save_checkpoint({'opinions_row': total_processed})

            logger.info(f"Processed {total_processed} opinions")

    async def process_opinion_chunk(self, df: pd.DataFrame):
        """Process a chunk of opinions"""

        async with self.db_pool.acquire() as conn:
            for _, row in df.iterrows():
                try:
                    # Generate case ID
                    case_id = row.get('id', '')
                    if not case_id:
                        # Generate from cluster ID or hash
                        case_id = hashlib.md5(
                            f"{row.get('cluster_id', '')}_{row.get('date_filed', '')}".encode()
                        ).hexdigest()

                    # Get court ID
                    court_name = row.get('court', '')
                    court_id = await self.get_court_id(conn, court_name)

                    # Clean text content
                    content = self.clean_text(row.get('text', '') or
                                             row.get('html', '') or
                                             row.get('plain_text', ''))

                    if not content:
                        continue

                    # Generate embedding (batched for efficiency)
                    embedding = await self.generate_embedding(content[:8000])

                    # Insert case
                    await conn.execute("""
                        INSERT INTO cases (
                            id, court_id, title, docket_number, decision_date,
                            reporter_cite, content, content_hash, embedding, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector, $10)
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                    """,
                        case_id,
                        court_id,
                        row.get('case_name', 'Unknown'),
                        row.get('docket_number'),
                        pd.to_datetime(row.get('date_filed'), errors='coerce'),
                        row.get('citation', ''),
                        content,
                        hashlib.sha256(content.encode()).hexdigest(),
                        embedding,
                        json.dumps({
                            'cluster_id': str(row.get('cluster_id', '')),
                            'author': row.get('author', ''),
                            'type': row.get('type', ''),
                            'source': 'bulk_import'
                        })
                    )

                    # Index in OpenSearch
                    await self.index_to_opensearch(case_id, row, content)

                except Exception as e:
                    logger.error(f"Error processing opinion: {e}")
                    continue

    async def load_citations(self, filename: str = "citations.csv.bz2"):
        """Load citation graph data"""

        # Download and decompress
        compressed_file = await self.download_file(filename)
        csv_file = self.decompress_file(compressed_file)

        logger.info("Loading citations data")

        # Process in chunks
        chunk_size = 5000
        total = 0

        for chunk in pd.read_csv(csv_file, chunksize=chunk_size):
            async with self.db_pool.acquire() as conn:
                for _, row in chunk.iterrows():
                    try:
                        # Map cluster IDs to case IDs
                        source_id = await self.get_case_by_cluster(conn, row.get('citing_opinion_id'))
                        target_id = await self.get_case_by_cluster(conn, row.get('cited_opinion_id'))

                        if source_id and target_id:
                            await conn.execute("""
                                INSERT INTO citations (
                                    source_case_id, target_case_id, context_span
                                ) VALUES ($1, $2, $3)
                                ON CONFLICT DO NOTHING
                            """,
                                source_id,
                                target_id,
                                row.get('citation_text', '')
                            )
                    except Exception as e:
                        logger.error(f"Error processing citation: {e}")
                        continue

            total += len(chunk)
            logger.info(f"Processed {total} citations")

    async def get_court_id(self, conn, court_name: str) -> Optional[int]:
        """Get court ID by name"""

        if not court_name:
            return None

        row = await conn.fetchrow(
            "SELECT id FROM courts WHERE name = $1 OR abbreviation = $1",
            court_name
        )

        if row:
            return row['id']

        # Create if not exists
        row = await conn.fetchrow("""
            INSERT INTO courts (name) VALUES ($1)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, court_name)

        return row['id']

    async def get_case_by_cluster(self, conn, cluster_id: str) -> Optional[str]:
        """Get case ID by cluster ID"""

        if not cluster_id:
            return None

        row = await conn.fetchrow(
            "SELECT id FROM cases WHERE metadata->>'cluster_id' = $1",
            str(cluster_id)
        )

        return row['id'] if row else None

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""

        if not text:
            return ""

        # Remove excessive whitespace
        text = " ".join(text.split())

        # Remove special characters that break parsing
        text = text.replace("\x00", "")

        # Limit length for storage
        if len(text) > 1000000:  # 1MB limit
            text = text[:1000000]

        return text

    async def generate_embedding(self, text: str) -> list:
        """Generate embeddings for text"""

        if not OPENAI_API_KEY:
            # Return random embedding for testing
            return [float(x) for x in np.random.rand(1536)]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "input": text[:8000],
                        "model": "text-embedding-3-small"
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    return response.json()["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")

        # Return zero embedding on error
        return [0.0] * 1536

    async def index_to_opensearch(self, case_id: str, row: pd.Series, content: str):
        """Index case in OpenSearch"""

        try:
            await self.osearch_client.index(
                index="cases",
                id=case_id,
                body={
                    "case_id": case_id,
                    "title": row.get('case_name', ''),
                    "court": row.get('court', ''),
                    "date": pd.to_datetime(row.get('date_filed'), errors='coerce'),
                    "content": content,
                    "docket_number": row.get('docket_number', ''),
                    "citation": row.get('citation', ''),
                    "cluster_id": str(row.get('cluster_id', ''))
                }
            )
        except Exception as e:
            logger.error(f"Error indexing to OpenSearch: {e}")

    def save_checkpoint(self, data: Dict[str, Any]):
        """Save import checkpoint for resume capability"""

        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f)

    def load_checkpoint(self) -> Dict[str, Any]:
        """Load import checkpoint"""

        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {}

    async def cleanup(self):
        """Close connections"""

        if self.db_pool:
            await self.db_pool.close()
        if self.osearch_client:
            await self.osearch_client.close()

async def main():
    """Main import process"""

    loader = BulkDataLoader()

    try:
        await loader.initialize()

        # Import order matters - courts first, then opinions, then citations
        logger.info("Starting bulk data import")

        # 1. Load courts (small, fast)
        await loader.load_courts()

        # 2. Load opinions (large, slow)
        await loader.load_opinions_chunked()

        # 3. Load citations (builds graph)
        await loader.load_citations()

        logger.info("Bulk import completed")

    finally:
        await loader.cleanup()

if __name__ == "__main__":
    asyncio.run(main())