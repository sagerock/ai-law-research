#!/usr/bin/env python3

"""
Initial Import Orchestrator
Coordinates the complete initial data import from CourtListener bulk files
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from workers.bulk_loader import BulkDataLoader
from workers.etl import LegalETLPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImportOrchestrator:
    """Orchestrates the complete initial import process"""

    def __init__(self):
        self.bulk_loader = BulkDataLoader()
        self.etl_pipeline = LegalETLPipeline()
        self.status_file = Path("./data/import_status.json")

    def load_status(self):
        """Load import status from file"""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {
            "courts": False,
            "opinions": False,
            "citations": False,
            "api_sync": False,
            "started_at": None,
            "completed_at": None
        }

    def save_status(self, status):
        """Save import status to file"""
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2, default=str)

    async def run_initial_import(self):
        """Run the complete initial import process"""

        status = self.load_status()

        if not status["started_at"]:
            status["started_at"] = datetime.now()
            self.save_status(status)

        try:
            # Initialize connections
            logger.info("Initializing database connections...")
            await self.bulk_loader.initialize()
            await self.etl_pipeline.initialize()

            # Step 1: Import Courts (if not done)
            if not status["courts"]:
                logger.info("\n" + "="*50)
                logger.info("STEP 1: Importing Courts Data")
                logger.info("="*50)
                await self.bulk_loader.load_courts()
                status["courts"] = True
                self.save_status(status)
            else:
                logger.info("Courts already imported, skipping...")

            # Step 2: Import Opinions (if not done)
            if not status["opinions"]:
                logger.info("\n" + "="*50)
                logger.info("STEP 2: Importing Opinions Data")
                logger.info("="*50)
                logger.info("This will take a while for large datasets...")
                await self.bulk_loader.load_opinions_chunked()
                status["opinions"] = True
                self.save_status(status)
            else:
                logger.info("Opinions already imported, skipping...")

            # Step 3: Import Citations (if not done)
            if not status["citations"]:
                logger.info("\n" + "="*50)
                logger.info("STEP 3: Building Citation Graph")
                logger.info("="*50)
                await self.bulk_loader.load_citations()
                status["citations"] = True
                self.save_status(status)
            else:
                logger.info("Citations already imported, skipping...")

            # Step 4: Sync recent updates via API
            if not status["api_sync"]:
                logger.info("\n" + "="*50)
                logger.info("STEP 4: Fetching Recent Updates via API")
                logger.info("="*50)
                # Fetch recent cases from major courts
                courts = ["scotus", "ca9", "ca2"]
                for court in courts:
                    logger.info(f"Fetching recent cases from {court}...")
                    await self.etl_pipeline.fetch_courtlistener_bulk(court, limit=20)

                status["api_sync"] = True
                self.save_status(status)
            else:
                logger.info("API sync already done, skipping...")

            # Mark completion
            status["completed_at"] = datetime.now()
            self.save_status(status)

            # Print summary
            await self.print_summary()

            logger.info("\n" + "="*50)
            logger.info("✅ INITIAL IMPORT COMPLETED SUCCESSFULLY!")
            logger.info("="*50)

        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise
        finally:
            await self.bulk_loader.cleanup()
            await self.etl_pipeline.cleanup()

    async def print_summary(self):
        """Print import summary statistics"""

        logger.info("\n" + "="*50)
        logger.info("IMPORT SUMMARY")
        logger.info("="*50)

        async with self.bulk_loader.db_pool.acquire() as conn:
            # Count statistics
            case_count = await conn.fetchval("SELECT COUNT(*) FROM cases")
            court_count = await conn.fetchval("SELECT COUNT(*) FROM courts")
            citation_count = await conn.fetchval("SELECT COUNT(*) FROM citations")

            logger.info(f"Courts imported: {court_count:,}")
            logger.info(f"Cases imported: {case_count:,}")
            logger.info(f"Citations imported: {citation_count:,}")

            # Top courts by case count
            top_courts = await conn.fetch("""
                SELECT c.name, COUNT(ca.id) as case_count
                FROM courts c
                JOIN cases ca ON ca.court_id = c.id
                GROUP BY c.name
                ORDER BY case_count DESC
                LIMIT 5
            """)

            logger.info("\nTop Courts by Case Count:")
            for row in top_courts:
                logger.info(f"  - {row['name']}: {row['case_count']:,} cases")

async def verify_environment():
    """Verify environment is properly configured"""

    required_vars = ["DATABASE_URL", "OPENSEARCH_URL"]
    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please set these in your .env file or environment")
        return False

    return True

async def main():
    """Main entry point"""

    print("""
    ╔══════════════════════════════════════════════╗
    ║   Legal Research Tool - Initial Data Import   ║
    ╚══════════════════════════════════════════════╝
    """)

    # Verify environment
    if not await verify_environment():
        sys.exit(1)

    # Check if data files exist
    data_dir = Path("./data/bulk")
    if not data_dir.exists() or not list(data_dir.glob("*.csv*")):
        logger.warning("No bulk data files found!")
        logger.info("Run './scripts/download_bulk.sh' first to download data files")
        sys.exit(1)

    # Run import
    orchestrator = ImportOrchestrator()

    try:
        await orchestrator.run_initial_import()
    except KeyboardInterrupt:
        logger.info("\nImport interrupted by user")
        logger.info("Run this script again to resume from checkpoint")
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())