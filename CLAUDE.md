# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sage's Study Group** - A free alternative to Quimbee for law students. Features AI-powered case briefs via Claude Sonnet 4.5, keyword search with citation ranking, citation network visualization, brief analysis, and personal library with bookmarks and collections.

**Target audience**: Law students who want free case briefs without paying $276/year for Quimbee.

**Branding**:
- Site name: "Sage's Study Group"
- Tagline: "Free AI Case Briefs for Law Students"
- HTML title: "Sage's Study Group | Free AI Case Briefs for Law Students"
- Domain: `lawstudygroup.com`

## Production Deployment (Railway)

The app is deployed on Railway with three services:

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | `lawstudygroup.com` | Next.js 16 app |
| Backend | `backend-production-8940.up.railway.app` | FastAPI server |
| Database | Railway PostgreSQL | Cases, citations, user library |

### Production Environment Variables

**Backend service:**
- `DATABASE_URL`: Railway PostgreSQL connection string
- `ANTHROPIC_API_KEY`: For Claude AI summaries
- `SUPABASE_JWT_SECRET`: For validating user auth tokens

**Frontend service:**
- `NEXT_PUBLIC_API_URL`: `https://backend-production-8940.up.railway.app`
- `NEXT_PUBLIC_SITE_URL`: `https://lawstudygroup.com` (for sitemap)
- `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase anonymous key

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

### Frontend (Next.js 16 with React 19)
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
- **SSR for case pages** - `generateMetadata()` for SEO (case names in browser tab + indexed by Google)
- `sitemap.ts` - Dynamic sitemap generated from database (auto-updates as cases are added)
- `robots.ts` - Allows search engine crawling
- Supabase authentication with JWT tokens

**Pages:**
- `/` - Homepage with search
- `/case/[id]` - Case detail with AI briefs, bookmarks, add to collection (SSR with dynamic metadata)
- `/briefcheck` - Brief analysis tool
- `/transparency` - Cost transparency dashboard
- `/library` - User's bookmarks and collections (requires auth)
- `/login` - User authentication
- `/shared/[id]` - Public shared collections

**Components:** `SearchInterface`, `CaseList`, `CaseCard`, `BriefUpload`, `CaseDetailClient`, `UserMenu`

### Workers (`workers/`)
- `etl.py`: `LegalETLPipeline` class - imports from CourtListener, generates embeddings, indexes to OpenSearch
- `bulk_loader.py`: Bulk data loading utilities for large imports

### Database Schema (PostgreSQL)

**Core tables** (`migrations/001_init.sql`):
- `cases`, `courts`, `citations`, `case_chunks`, `treatments`, `ai_summaries`, `collections`, `collection_cases`

**Casebook tracking** (`migrations/002_casebooks.sql`):
- `casebooks`, `casebook_cases`, `chapters`

**Transparency & donations** (`migrations/003_transparency_tracking.sql`, `004_donations_tracking.sql`):
- `api_usage_log` - Tracks AI API calls per day for cost transparency
- `site_config` - Editable config values (hosting cost, Ko-fi username, charity info)
- `donations` - Ko-fi webhook donations (auto-populated via webhook)

**User library** (`migrations/005_user_library.sql`):
- `profiles` - User profiles (synced from Supabase auth)
- `bookmarks` - Saved cases per user
- Adds `subject` column to `collections`

### External Services

**Production (Railway):**
- **Railway PostgreSQL**: Primary database
- **Anthropic API**: Claude Sonnet 4.5 for AI case summaries (~$0.03/summary)
- **CourtListener**: Case data source (bulk CSV imports)
- **Ko-fi**: Donation platform (webhook integration)
- **Supabase**: User authentication (JWT tokens validated by backend)

**Local Development (Docker):**
- **PostgreSQL + pgvector**: Local database with optional vector similarity search
- **OpenSearch**: Optional BM25 keyword search
- **Redis**: Optional caching layer

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
GET  /api/v1/transparency           # Get cost/donation stats for dashboard
POST /api/v1/kofi-webhook           # Receive Ko-fi donation webhooks
GET  /api/v1/sitemap/cases          # Get all case IDs for sitemap generation

# Library endpoints (require auth)
GET  /api/v1/library/collections              # List user's collections
POST /api/v1/library/collections              # Create collection
GET  /api/v1/library/collections/{id}         # Get collection with cases
PUT  /api/v1/library/collections/{id}         # Update collection
DELETE /api/v1/library/collections/{id}       # Delete collection
POST /api/v1/library/collections/{id}/cases   # Add case to collection
DELETE /api/v1/library/collections/{id}/cases/{case_id}  # Remove case
GET  /api/v1/library/bookmarks                # List user's bookmarks
POST /api/v1/library/bookmarks                # Add bookmark
DELETE /api/v1/library/bookmarks/{case_id}    # Remove bookmark
GET  /api/v1/library/bookmarks/check/{case_id}  # Check if bookmarked
GET  /api/v1/shared/{collection_id}           # Get public collection (no auth)
```

## User Library Feature

Users can save cases and organize them:

**Bookmarks**: Quick-save individual cases from the case detail page
- Click bookmark icon on any case
- View all bookmarks in My Library > Bookmarks tab

**Collections**: Organize cases into named groups
- Create collections with name, description, subject tag
- Add/remove cases from collections via case detail page dropdown
- Make collections public to share with others
- Public collections accessible at `/shared/{collection_id}`

## Transparency Dashboard

The `/transparency` page shows real-time costs and donations:
- Monthly AI costs (tracked per summary in `api_usage_log`)
- Monthly hosting costs (configured in `site_config`)
- Donations received (auto-tracked via Ko-fi webhook)
- Progress bars showing donations vs costs
- Surplus goes to Houseless Movement charity

**Ko-fi webhook URL**: `https://backend-production-8940.up.railway.app/api/v1/kofi-webhook`

**Configurable values** (via `site_config` table):
```sql
UPDATE site_config SET value = 'your-username' WHERE key = 'kofi_username';
UPDATE site_config SET value = 'https://charity-url.org' WHERE key = 'charity_url';
UPDATE site_config SET value = '10.00' WHERE key = 'monthly_hosting_cost';
```

## SEO

- **Custom domain**: `lawstudygroup.com`
- **Dynamic page titles**: Case pages show "Erie Railroad v. Tompkins | Sage's Study Group"
- **Server-side rendering**: Case metadata generated on server for search engine indexing
- **Sitemap**: `/sitemap.xml` dynamically lists all cases from database (revalidates hourly)
- **Robots.txt**: `/robots.txt` allows crawling, points to sitemap

New cases are automatically added to the sitemap when inserted into the database.

## Key Patterns

- Database connections use `asyncpg` with connection pooling
- Production search uses PostgreSQL ILIKE with citation count ranking
- AI summaries generated via Claude Sonnet 4.5, cached in `ai_summaries` table
- AI usage logged to `api_usage_log` for transparency dashboard
- Citation network stored in `citations` table
- Case pages use SSR with `generateMetadata()` for SEO
- Ko-fi donations auto-tracked via webhook
- User auth via Supabase JWT tokens, validated in backend with `SUPABASE_JWT_SECRET`
- Collection IDs are integers (SERIAL) - backend casts string params to int

## Environment Variables

**Required:**
- `DATABASE_URL`: PostgreSQL connection string

**For AI Summaries (production):**
- `ANTHROPIC_API_KEY`: Claude API key for case summaries

**For User Auth (production):**
- `SUPABASE_JWT_SECRET`: Secret for validating Supabase JWT tokens

**For SEO (production):**
- `NEXT_PUBLIC_SITE_URL`: `https://lawstudygroup.com` for sitemap generation

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
