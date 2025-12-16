# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A legal research tool designed as a free alternative to Westlaw/Lexis for solo lawyers and small firms. Features hybrid search (BM25 + semantic), AI-powered case summaries via GPT-5-mini, brief analysis with citation extraction, and CourtListener webhook integration.

## Development Commands

### Infrastructure
```bash
docker-compose up -d           # Start all services (Postgres, OpenSearch, Redis)
docker-compose down            # Stop services
docker-compose down -v         # Stop and remove volumes (resets database)
docker restart legal-backend   # Restart backend after OpenSearch is ready
```

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python simple_api.py           # Simplified API for local dev (port 8000)
# OR
uvicorn main:app --reload      # Full API with OpenSearch integration
```

### Frontend (Next.js 15 with React 19)
```bash
cd frontend
npm install
npm run dev                    # Runs on port 3000 with Turbopack
npm run build                  # Production build
```

### Make Commands
```bash
make setup   # Initial Docker setup (copies .env.example, builds containers)
make dev     # Start all services
make etl     # Run ETL pipeline in worker container
make logs    # View container logs
make clean   # Remove containers AND volumes
```

## Architecture

### Backend (`backend/`)
- `main.py`: Full FastAPI server with OpenSearch integration, used in Docker/production
- `simple_api.py`: Simplified API for local development, direct PostgreSQL queries
- `brief_analyzer.py`: Citation extraction using eyecite library, validates against database, detects legal areas
- `webhooks.py`: CourtListener webhook handlers for real-time case updates

### Frontend (`frontend/`)
- Next.js 15 App Router with Turbopack
- React 19 with Tailwind CSS v4
- Pages: `/` (search), `/case/[id]` (case detail), `/briefcheck` (brief analysis)
- Components: `SearchInterface`, `CaseList`, `CaseCard`, `BriefUpload`

### Workers (`workers/`)
- `etl.py`: `LegalETLPipeline` class - imports from CourtListener, generates embeddings, indexes to OpenSearch
- `bulk_loader.py`: Bulk data loading utilities for large imports

### Database Schema (PostgreSQL + pgvector)
- `migrations/001_init.sql`: Core schema (cases, courts, citations, case_chunks, treatments)
- `migrations/002_casebooks.sql`: Law school casebook tracking (casebooks, casebook_cases, chapters)
- Vector embeddings use 1536 dimensions (OpenAI text-embedding-3-small)
- IVFFlat indexes for similarity search

### External Services
- **PostgreSQL + pgvector**: Primary database with vector similarity search
- **OpenSearch**: BM25 keyword search (cases index with legal_analyzer)
- **Redis**: Caching layer for API responses
- **OpenAI API**: GPT-5-mini for summaries, text-embedding-3-small for embeddings
- **CourtListener API**: Case data source, webhook integration
- **Supabase**: Optional cloud PostgreSQL for production

## Available Bulk Data

Located in `data/courtlistener/`:
- `opinions-2025-12-02.csv` (321 GB): Full opinion text for all cases
- `opinion-clusters-2025-12-02.csv` (12 GB): Case metadata (74.5M records)
- `citation-map-2025-12-02.csv` (2.6 GB): Citation relationships (76M records)
- `citations.db` (4.1 GB): Pre-processed SQLite citation database
- `courts-2025-12-02.csv`: Court metadata

Curated data in `data/`:
- `1L_core_cases.json`: Foundation law school cases by subject with CourtListener IDs
- `torts_top50_matched.json`: Top torts cases matched to CourtListener

## Key API Endpoints

```
GET  /health                    # Service health check
POST /api/v1/search             # Search cases (query, search_type, limit)
GET  /api/v1/case/{id}          # Get case details
GET  /api/v1/case/{id}/summary  # Get/generate AI summary
POST /api/v1/briefcheck         # Analyze uploaded brief
GET  /api/v1/citator/{id}       # Get citation treatment for case
```

## Key Patterns

- Database connections use `asyncpg` with connection pooling
- Search combines ILIKE keyword matching with citation count ordering (semantic search WIP)
- AI summaries generated on-demand, cached in database (~$0.002/summary)
- Citation extraction uses eyecite library with custom patterns for missed citations
- Brief analyzer detects legal areas and suggests foundation cases
- Docker backend depends on OpenSearch being ready; may need manual restart

## Environment Variables

Required in `.env`:
- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: For AI summaries and embeddings
- `COURTLISTENER_API_KEY`: For case imports
- `SUPABASE_URL` / `SUPABASE_ANON_KEY`: For production database (optional)
- `OPENSEARCH_URL`: Default http://localhost:9200
- `REDIS_URL`: Default redis://localhost:6379

## Import Scripts

```bash
python scripts/import_ohio_cases.py      # Import Ohio court cases via API
python scripts/import_from_huggingface.py # Import from HuggingFace datasets
python scripts/fetch_full_opinions.py    # Fetch full opinion text for existing cases
python scripts/setup_bulk_data.py        # Set up bulk data import from CSVs
python scripts/import_casebook.py        # Import casebook case lists
python scripts/sync_to_production.py     # Sync local DB to production
```
