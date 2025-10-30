# Deployment Guide - Legal Research Tool

## Architecture Overview

This application uses a multi-service architecture:
- **Frontend**: Next.js (React)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (with pgvector)
- **Search**: OpenSearch
- **Cache**: Redis

## Deployment Strategy: Railway + Managed OpenSearch

### Step 1: Set up Managed OpenSearch

We'll use **Bonsai.io** (free tier available) for OpenSearch hosting.

#### Option A: Bonsai.io (Recommended - Free Tier)
1. Go to https://bonsai.io/signup
2. Create a free account
3. Create a new cluster:
   - Name: `legal-research`
   - Version: OpenSearch 2.x
   - Plan: Sandbox (Free)
4. Once created, copy the **Cluster URL** (looks like: `https://xxxxx.us-east-1.bonsaisearch.net:443`)

#### Option B: AWS OpenSearch (Production)
1. Go to AWS Console → OpenSearch Service
2. Create domain with minimal specs (t3.small.search)
3. Copy the domain endpoint

### Step 2: Create Railway Project

```bash
# Login to Railway
railway login

# Create new project (from the project directory)
cd "/Volumes/T7/Scripts/AI Law Researcher/legal-research-tool"
railway init
```

### Step 3: Add Services to Railway

#### 3a. Add PostgreSQL
```bash
railway add --database postgresql
```

#### 3b. Add Redis
```bash
railway add --database redis
```

### Step 4: Set Environment Variables

Set these in Railway dashboard or via CLI:

#### Backend Service Variables
```bash
# Database (automatically set by Railway)
DATABASE_URL=<set by Railway PostgreSQL>

# OpenSearch (from Bonsai.io)
OPENSEARCH_URL=https://xxxxx.bonsaisearch.net:443

# Redis (automatically set by Railway)
REDIS_URL=<set by Railway Redis>

# Optional: OpenAI API Key (for semantic search)
OPENAI_API_KEY=<your-key-if-you-have-one>
```

You can set these via Railway CLI:
```bash
railway variables set OPENSEARCH_URL="https://xxxxx.bonsaisearch.net:443"
```

Or via the Railway Dashboard:
1. Go to https://railway.app/
2. Select your project
3. Click on backend service → Variables
4. Add each variable

### Step 5: Deploy Backend

```bash
# Link to Railway project
railway link

# Deploy backend
railway up

# Check deployment status
railway status

# View logs
railway logs
```

### Step 6: Deploy Frontend

The frontend needs to be deployed as a separate service:

```bash
# Create new service for frontend
railway service create frontend

# Set frontend environment variable
railway variables set NEXT_PUBLIC_API_URL="https://your-backend-url.railway.app" --service frontend
```

Create `frontend/railway.toml`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "npm run build && npm run start"
```

Then deploy:
```bash
railway up --service frontend
```

### Step 7: Initialize Database Schema

After backend is deployed, you need to run migrations:

```bash
# Connect to production database
railway run psql $DATABASE_URL -f migrations/001_initial_schema.sql
```

Or use Railway's console to run SQL directly.

### Step 8: Import Initial Data

You have 102 cases locally. To import them to production:

1. Update `scripts/sync_to_opensearch.py` to work with production URLs
2. Export your local PostgreSQL data
3. Import to Railway PostgreSQL
4. Run sync script to populate OpenSearch

```bash
# Export local data
docker-compose exec postgres pg_dump -U legal_user -d legal_research -t cases -t courts > production_data.sql

# Import to Railway
railway run psql $DATABASE_URL < production_data.sql

# Sync to production OpenSearch
# Update OPENSEARCH_URL and DATABASE_URL in script first, then:
python3 scripts/sync_to_opensearch.py
```

### Step 9: Verify Deployment

1. Check backend health: `https://your-backend.railway.app/`
2. Check frontend: `https://your-frontend.railway.app/`
3. Test search functionality
4. Verify cases are showing up

## Environment Variables Reference

### Backend Required:
- `DATABASE_URL` - PostgreSQL connection (set by Railway)
- `OPENSEARCH_URL` - Your Bonsai.io URL
- `REDIS_URL` - Redis connection (set by Railway)

### Backend Optional:
- `OPENAI_API_KEY` - For AI-powered semantic search
- `SUPABASE_URL` - If using Supabase features
- `SUPABASE_ANON_KEY` - If using Supabase features

### Frontend Required:
- `NEXT_PUBLIC_API_URL` - Backend URL from Railway

## Cost Estimate

- **Railway**: $5-20/month (PostgreSQL + Redis + Backend)
- **Bonsai.io Free**: $0/month (up to 125MB, 10k docs)
- **Bonsai.io Paid**: $10+/month for production
- **Vercel (alternative frontend)**: Free tier available

**Total estimated**: $5-30/month depending on usage

## Troubleshooting

### Backend won't start
- Check logs: `railway logs`
- Verify environment variables are set
- Check that DATABASE_URL and OPENSEARCH_URL are correct

### Frontend can't connect to backend
- Verify NEXT_PUBLIC_API_URL is set correctly
- Check CORS settings in backend/main.py
- Ensure backend is deployed and healthy

### No search results
- Verify OpenSearch connection
- Check that data was synced to OpenSearch
- Test OpenSearch directly: `curl $OPENSEARCH_URL/cases/_count`

### Database connection errors
- Check DATABASE_URL format
- Verify Railway PostgreSQL is running
- Run migrations if tables don't exist

## Next Steps After Deployment

1. Set up custom domain (optional)
2. Enable HTTPS (Railway does this automatically)
3. Set up monitoring/alerting
4. Import more cases from HuggingFace
5. Enable semantic search with OpenAI API key
6. Add authentication if needed

## Rollback

If deployment fails:
```bash
# Revert to previous deployment
railway rollback

# Check previous deployments
railway deployments
```
