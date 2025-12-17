# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A legal research tool designed as a free alternative to Westlaw/Lexis for solo lawyers and small firms. Features keyword search with citation ranking, AI-powered case summaries via Claude Sonnet 4.5, citation network visualization, and brief analysis with citation extraction.

## Production Deployment (Railway)

The app is deployed on Railway with three services:

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | `ai-law-research-production.up.railway.app` | Next.js 16 app |
| Backend | `backend-production-8940.up.railway.app` | FastAPI server |
| Database | Railway PostgreSQL | 548 cases, 184 citations |

### Production Environment Variables

**Backend service:**
- `DATABASE_URL`: Railway PostgreSQL connection string
- `ANTHROPIC_API_KEY`: For Claude AI summaries

**Frontend service:**
- `NEXT_PUBLIC_API_URL`: `https://backend-production-8940.up.railway.app`

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
- `main.py`: Production FastAPI server (Railway deployment), supports optional OpenSearch/Redis
- `simple_api.py`: Simplified API for local development, direct PostgreSQL queries
- `brief_analyzer.py`: Citation extraction using eyecite library, validates against database, detects legal areas
- `railway.toml`: Railway deployment config (Dockerfile builder)
- `Dockerfile`: Production container with Python 3.11

### Frontend (`frontend/`)
- Next.js 16 App Router with Turbopack (requires Node.js 20+)
- React 19 with Tailwind CSS v4
- Pages: `/` (search), `/case/[id]` (case detail with citation sidebar), `/briefcheck` (brief analysis)
- Components: `SearchInterface`, `CaseList`, `CaseCard`, `BriefUpload`
- `railway.toml`: Railway deployment config (Nixpacks with Node 20)

### Workers (`workers/`)
- `etl.py`: `LegalETLPipeline` class - imports from CourtListener, generates embeddings, indexes to OpenSearch
- `bulk_loader.py`: Bulk data loading utilities for large imports

### Database Schema (PostgreSQL + pgvector)
- `migrations/001_init.sql`: Core schema (cases, courts, citations, case_chunks, treatments)
- `migrations/002_casebooks.sql`: Law school casebook tracking (casebooks, casebook_cases, chapters)
- Vector embeddings use 1536 dimensions (OpenAI text-embedding-3-small)
- IVFFlat indexes for similarity search

### External Services

**Production (Railway):**
- **Railway PostgreSQL**: Primary database (no pgvector - uses ILIKE search with citation ranking)
- **Anthropic API**: Claude Sonnet 4.5 for AI case summaries (~$0.03/summary)
- **CourtListener**: Case data source (bulk CSV imports)

**Local Development (Docker):**
- **PostgreSQL + pgvector**: Local database with optional vector similarity search
- **OpenSearch**: Optional BM25 keyword search (cases index with legal_analyzer)
- **Redis**: Optional caching layer for API responses
- **OpenAI API**: Optional embeddings (text-embedding-3-small)

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
GET  /health                        # Service health check
POST /api/v1/search                 # Search cases (query, search_type, limit)
GET  /api/v1/cases/{id}             # Get case details
GET  /api/v1/cases/{id}/summary     # Get cached AI summary
POST /api/v1/cases/{id}/summarize   # Generate new AI summary (uses Claude)
GET  /api/v1/cases/{id}/citations   # Get citing/cited cases
GET  /api/v1/cases/{id}/citator     # Get citation treatment badge
POST /api/v1/briefcheck             # Analyze uploaded brief
```

## Key Patterns

- Database connections use `asyncpg` with connection pooling
- Production search uses PostgreSQL ILIKE with citation count ranking (no pgvector on Railway)
- AI summaries generated via Claude Sonnet 4.5, cached in `ai_summaries` table (~$0.03/summary)
- Citation network stored in `citations` table (184 relationships between 548 cases)
- Citation extraction uses eyecite library with custom patterns for missed citations
- Backend gracefully handles missing OpenSearch/Redis (optional services)

## Environment Variables

**Required:**
- `DATABASE_URL`: PostgreSQL connection string

**For AI Summaries (production):**
- `ANTHROPIC_API_KEY`: Claude API key for case summaries

**Optional (local development):**
- `OPENAI_API_KEY`: For embeddings (text-embedding-3-small)
- `OPENSEARCH_URL`: Default http://localhost:9200
- `REDIS_URL`: Default redis://localhost:6379
- `COURTLISTENER_API_KEY`: For API-based case imports

## Import Scripts

```bash
python scripts/import_casebook.py        # Import 1L landmark cases from JSON
python scripts/import_citations_local.py # Build citation network from bulk CSV
python scripts/fetch_full_opinions.py    # Fetch full opinion text for existing cases
python scripts/setup_bulk_data.py        # Set up bulk data import from CSVs
python scripts/sync_to_production.py     # Sync local DB to production (Railway)
```
