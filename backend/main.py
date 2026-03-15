from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import io
import asyncpg
import httpx
from opensearchpy._async.client import AsyncOpenSearch
import redis.asyncio as redis
import numpy as np
from datetime import datetime, date
import time
import json
import re
import random
from jose import jwt, JWTError
from uuid import UUID
from cryptography.fernet import Fernet, InvalidToken

app = FastAPI(title="Legal Research API", version="1.0.0")

# CORS configuration - Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection pools
db_pool = None
osearch_client = None
redis_client = None

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL")  # Optional - falls back to PostgreSQL search
REDIS_URL = os.getenv("REDIS_URL")  # Optional - caching disabled if not set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # Fernet key for encrypting user API keys

# BYOK encryption helpers
_fernet = None

def get_fernet():
    global _fernet
    if _fernet is None:
        if not ENCRYPTION_KEY:
            raise HTTPException(status_code=500, detail="ENCRYPTION_KEY not configured")
        _fernet = Fernet(ENCRYPTION_KEY.encode())
    return _fernet


def encrypt_api_key(key: str) -> str:
    return get_fernet().encrypt(key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    return get_fernet().decrypt(encrypted.encode()).decode()


def make_key_preview(key: str) -> str:
    if len(key) <= 12:
        return key[:4] + "..." + key[-4:]
    return key[:10] + "..." + key[-4:]


async def get_user_api_key(user_id: str) -> Optional[str]:
    """Get decrypted API key for a user, or None."""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT encrypted_api_key FROM profiles WHERE id = $1",
                user_id,
            )
            if row and row["encrypted_api_key"]:
                return decrypt_api_key(row["encrypted_api_key"])
    except Exception as e:
        print(f"Warning: Failed to decrypt user API key: {e}")
    return None


async def get_anthropic_api_key(user_id: Optional[str] = None) -> tuple[str, str]:
    """
    Returns (api_key, source) where source is 'byok' or 'site'.
    Tries user key first, falls back to site key.
    """
    if user_id:
        user_key = await get_user_api_key(user_id)
        if user_key:
            return user_key, "byok"
    if ANTHROPIC_API_KEY:
        return ANTHROPIC_API_KEY, "site"
    raise HTTPException(status_code=503, detail="AI service not configured")

# Pydantic models
class SearchQuery(BaseModel):
    query: str
    jurisdiction: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 10
    search_type: str = "hybrid"  # hybrid, keyword, semantic

class Case(BaseModel):
    id: str
    title: str
    court: str
    date: str
    reporter_cite: Optional[str]
    content: str
    snippet: Optional[str]
    score: Optional[float]
    citator_badge: Optional[str]

class BriefCheckRequest(BaseModel):
    content: str
    check_citations: bool = True
    find_missing_authorities: bool = True
    check_treatments: bool = True

class CitatorResult(BaseModel):
    case_id: str
    badge: str  # green, yellow, red
    citing_cases: List[Dict]
    negative_treatments: List[Dict]
    positive_treatments: List[Dict]


# Library feature models
class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject: Optional[str] = None
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    is_public: Optional[bool] = None


class AddCaseToCollection(BaseModel):
    case_id: str
    notes: Optional[str] = None


class AddLegalTextToCollection(BaseModel):
    legal_text_item_id: int
    notes: Optional[str] = None


class ReorderItem(BaseModel):
    type: str       # "case" or "legal_text"
    id: str         # case_id or str(legal_text_item_id)


class ReorderRequest(BaseModel):
    items: List[ReorderItem]


class BookmarkCreate(BaseModel):
    case_id: str
    folder: Optional[str] = None
    notes: Optional[str] = None


# Comment models
class CommentCreate(BaseModel):
    content: str


class CommentUpdate(BaseModel):
    content: str


class SummaryRating(BaseModel):
    rating: int  # 1, -1, or 0 to remove


class CommentVote(BaseModel):
    vote_type: int  # 1, -1, or 0 to remove


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    law_school: Optional[str] = None
    graduation_year: Optional[int] = None
    is_public: Optional[bool] = None


class ApiKeyRequest(BaseModel):
    anthropic_api_key: str


class OutlineCreate(BaseModel):
    title: str
    subject: str
    professor: Optional[str] = None
    law_school: Optional[str] = None
    semester: Optional[str] = None
    description: Optional[str] = None
    filename: str
    file_url: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    is_public: bool = True


# JWT Authentication helper
async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Validate Supabase JWT and return user info.
    Returns None if no valid token (for optional auth endpoints).
    """
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    if not SUPABASE_JWT_SECRET:
        print("Warning: SUPABASE_JWT_SECRET not configured")
        return None

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role")
        }
    except JWTError as e:
        print(f"JWT validation error: {e}")
        if "expired" in str(e).lower():
            raise HTTPException(status_code=401, detail="Token expired")
        return None


async def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Require authentication - raises 401 if not authenticated"""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    # Backfill email on profiles table (fire-and-forget)
    try:
        if db_pool and user.get("email"):
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE profiles SET email = $1 WHERE id = $2 AND (email IS NULL OR email != $1)",
                    user["email"], user["id"],
                )
    except Exception:
        pass
    return user


# Admin authentication
ADMIN_EMAIL = "sage@sagerock.com"


async def require_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Require admin authentication - raises 403 if not admin"""
    user = await require_auth(authorization)
    if user.get("email") != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class AdminUserUpdate(BaseModel):
    tier: Optional[str] = None
    daily_limit: Optional[int] = None
    model_override: Optional[str] = None


# Transparency dashboard helper
async def log_api_usage(usage_type: str, input_tokens: int, output_tokens: int, cost: float, source: str = "site"):
    """Log API usage for transparency dashboard tracking"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO api_usage_log (usage_date, usage_type, call_count, input_tokens, output_tokens, estimated_cost, source, updated_at)
                VALUES (CURRENT_DATE, $1, 1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
                ON CONFLICT (usage_date, usage_type) DO UPDATE SET
                    call_count = api_usage_log.call_count + 1,
                    input_tokens = api_usage_log.input_tokens + EXCLUDED.input_tokens,
                    output_tokens = api_usage_log.output_tokens + EXCLUDED.output_tokens,
                    estimated_cost = api_usage_log.estimated_cost + EXCLUDED.estimated_cost,
                    updated_at = CURRENT_TIMESTAMP
            """, usage_type, input_tokens, output_tokens, cost, source)
        # Also debit the community pool for site-funded AI calls
        if source == "site" and cost > 0:
            try:
                await debit_pool(cost, usage_type, None)
            except Exception as pool_err:
                print(f"Warning: Failed to debit pool: {pool_err}")
    except Exception as e:
        # Don't fail the main request if logging fails
        print(f"Warning: Failed to log API usage: {e}")


# --- Community AI Pool helpers ---

async def get_pool_balance() -> float:
    """Get current community pool balance from ledger."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) as balance FROM pool_ledger")
        return float(row["balance"])


async def debit_pool(amount: float, description: str, reference_id: str | None) -> float:
    """Debit the pool using advisory lock to prevent overdraw. Returns new balance."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Serialize debits to prevent overdraw
            await conn.execute("SELECT pg_advisory_xact_lock(1)")
            await conn.execute(
                "INSERT INTO pool_ledger (amount, entry_type, description, reference_id, created_by) VALUES ($1, 'ai_debit', $2, $3, 'system')",
                -abs(amount), description, reference_id
            )
            row = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) as balance FROM pool_ledger")
            return float(row["balance"])


async def credit_pool(amount: float, entry_type: str, description: str, reference_id: str | None, created_by: str) -> float:
    """Credit the pool. Returns new balance."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO pool_ledger (amount, entry_type, description, reference_id, created_by) VALUES ($1, $2, $3, $4, $5)",
            abs(amount), entry_type, description, reference_id, created_by
        )
        row = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) as balance FROM pool_ledger")
        return float(row["balance"])


async def check_pool_available(user_id: str | None) -> bool:
    """Check if pool has funds. BYOK users always pass."""
    if user_id:
        user_key = await get_user_api_key(user_id)
        if user_key:
            return True
    balance = await get_pool_balance()
    return balance > 0


POOL_EMPTY_DETAIL = "Community AI pool is empty. Donate to refill it!"


@app.on_event("startup")
async def startup():
    global db_pool, osearch_client, redis_client

    # Initialize PostgreSQL connection pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

    # Ensure rating/voting tables exist
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS summary_ratings (
                    id SERIAL PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating IN (-1, 1)),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(case_id, user_id)
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_ratings_case_id ON summary_ratings(case_id)")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_votes (
                    id SERIAL PRIMARY KEY,
                    comment_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    vote_type INTEGER NOT NULL CHECK (vote_type IN (-1, 1)),
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(comment_id, user_id)
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_comment_votes_comment_id ON comment_votes(comment_id)")
            # Backfill Dressler textbook metadata
            await conn.execute("""
                UPDATE casebooks SET edition = '10th', year = 2022
                WHERE title = 'Criminal Law: Cases and Materials'
                  AND authors LIKE '%Dressler%' AND edition IS NULL
            """)
            print("Rating/voting tables ready")
    except Exception as e:
        print(f"Warning: could not create rating tables: {e}")

    # Initialize OpenSearch client (optional)
    if OPENSEARCH_URL:
        try:
            use_ssl = OPENSEARCH_URL.startswith('https://')
            osearch_client = AsyncOpenSearch(
                hosts=[OPENSEARCH_URL],
                http_compress=True,
                use_ssl=use_ssl,
                verify_certs=False,
            )
            await ensure_opensearch_indices()
            print(f"OpenSearch connected: {OPENSEARCH_URL}")
        except Exception as e:
            print(f"OpenSearch not available: {e}")
            osearch_client = None
    else:
        print("OpenSearch not configured - using PostgreSQL search")

    # Initialize Redis client (optional)
    if REDIS_URL:
        try:
            redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
            await redis_client.ping()
            print(f"Redis connected: {REDIS_URL}")
        except Exception as e:
            print(f"Redis not available: {e}")
            redis_client = None
    else:
        print("Redis not configured - caching disabled")

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()
    if osearch_client:
        await osearch_client.close()
    if redis_client:
        await redis_client.close()

async def ensure_opensearch_indices():
    """Create OpenSearch indices if they don't exist"""
    cases_index = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "legal_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop", "porter_stem"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "legal_analyzer"},
                "content": {"type": "text", "analyzer": "legal_analyzer"},
                "court_id": {"type": "integer"},
                "court_name": {"type": "text"},
                "decision_date": {"type": "date"},
                "reporter_cite": {"type": "keyword"},
                "metadata": {"type": "object"},
                "source_url": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    }
    
    if not await osearch_client.indices.exists(index="cases"):
        await osearch_client.indices.create(index="cases", body=cases_index)

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway - returns 200 OK even if services are slow"""
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "opensearch": "not configured",
        "redis": "not configured"
    }

    # Check database (required)
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"

    # Check OpenSearch (optional)
    if osearch_client:
        try:
            opensearch_health = await osearch_client.cluster.health()
            health_status["opensearch"] = opensearch_health.get("status", "connected")
        except Exception as e:
            health_status["opensearch"] = f"error: {str(e)[:50]}"

    # Check Redis (optional)
    if redis_client:
        try:
            await redis_client.ping()
            health_status["redis"] = "connected"
        except Exception as e:
            health_status["redis"] = f"error: {str(e)[:50]}"

    # Always return 200 OK so Railway considers the deployment healthy
    return health_status

@app.post("/api/v1/search")
async def search_cases(query: SearchQuery):
    """Hybrid search combining BM25 and semantic search"""

    # Check cache first (if Redis available)
    cache_key = f"search:{json.dumps(query.dict(), sort_keys=True)}"
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass

    results = []
    keyword_results = []
    semantic_results = []

    if query.search_type in ["hybrid", "keyword"]:
        # Use OpenSearch if available, otherwise PostgreSQL
        if osearch_client:
            keyword_results = await keyword_search(query)
        else:
            keyword_results = await postgres_search(query)
        results.extend(keyword_results)

    # Only do semantic search if OpenAI API key is configured
    if query.search_type in ["hybrid", "semantic"] and OPENAI_API_KEY:
        try:
            # Semantic search via pgvector
            semantic_results = await semantic_search(query)
            results.extend(semantic_results)
        except Exception as e:
            # If semantic search fails, just use keyword results
            print(f"Semantic search failed: {e}")
            pass

    if query.search_type == "hybrid" and semantic_results:
        # Reciprocal Rank Fusion only if we have both result sets
        results = reciprocal_rank_fusion(keyword_results, semantic_results)

    # Cache results (if Redis available)
    if redis_client:
        try:
            await redis_client.setex(cache_key, 300, json.dumps(results))
        except:
            pass

    return results

async def keyword_search(query: SearchQuery):
    """BM25 keyword search using OpenSearch with title and citation boosting"""

    search_body = {
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": [
                            # Exact phrase match in title - highest boost
                            {
                                "match_phrase": {
                                    "title": {
                                        "query": query.query,
                                        "boost": 20
                                    }
                                }
                            },
                            # Word match in title - high boost
                            {
                                "match": {
                                    "title": {
                                        "query": query.query,
                                        "boost": 10
                                    }
                                }
                            },
                            # Match in content
                            {
                                "match": {
                                    "content": {
                                        "query": query.query,
                                        "operator": "or"
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1,
                        "filter": []
                    }
                },
                # Boost by citation count - landmark cases rank higher
                "functions": [
                    {
                        "field_value_factor": {
                            "field": "citation_count",
                            "factor": 0.0001,
                            "modifier": "log1p",
                            "missing": 1
                        }
                    }
                ],
                "boost_mode": "multiply",
                "score_mode": "multiply"
            }
        },
        "size": query.limit,
        "highlight": {
            "fields": {
                "title": {},
                "content": {
                    "fragment_size": 200,
                    "number_of_fragments": 1
                }
            }
        }
    }
    
    # Add filters (nested inside function_score > query > bool)
    filters = search_body["query"]["function_score"]["query"]["bool"]["filter"]
    if query.jurisdiction:
        filters.append({"term": {"court_id": query.jurisdiction}})

    if query.date_from:
        filters.append({"range": {"decision_date": {"gte": query.date_from}}})

    if query.date_to:
        filters.append({"range": {"decision_date": {"lte": query.date_to}}})
    
    response = await osearch_client.search(index="cases", body=search_body)

    results = []
    for hit in response["hits"]["hits"]:
        case = hit["_source"]
        case["id"] = hit["_id"]  # Extract document ID from OpenSearch
        case["score"] = hit["_score"]
        if "highlight" in hit:
            case["snippet"] = hit["highlight"]["content"][0]
        results.append(case)

    return results

async def postgres_search(query: SearchQuery):
    """Search using PostgreSQL full-text search with ts_rank for relevance scoring"""

    # Convert query to tsquery format (handles multiple words)
    # plainto_tsquery handles natural language input
    sql = """
        SELECT
            c.id, c.title, c.court_id, c.decision_date,
            c.reporter_cite, c.content, c.metadata,
            ct.name as court_name,
            COALESCE((c.metadata->>'citation_count')::int, 0) as citation_count,
            (
                -- Title relevance (weighted 10x)
                COALESCE(ts_rank(to_tsvector('english', c.title), plainto_tsquery('english', $1)), 0) * 10 +
                -- Content relevance
                COALESCE(ts_rank(to_tsvector('english', COALESCE(c.content, '')), plainto_tsquery('english', $1)), 0) +
                -- Boost for exact title match
                CASE WHEN c.title ILIKE $2 THEN 5 ELSE 0 END +
                -- Citation count boost (log scale to prevent domination)
                LN(GREATEST(COALESCE((c.metadata->>'citation_count')::int, 0), 1) + 1) * 0.1
            ) as score
        FROM cases c
        LEFT JOIN courts ct ON c.court_id = ct.id
        WHERE
            c.content IS NOT NULL AND c.content != ''
            AND (
                to_tsvector('english', c.title) @@ plainto_tsquery('english', $1)
                OR to_tsvector('english', c.content) @@ plainto_tsquery('english', $1)
                OR c.title ILIKE $2
            )
    """

    params = [query.query, f"%{query.query}%"]
    param_count = 2

    if query.jurisdiction:
        param_count += 1
        sql += f" AND c.court_id = ${param_count}"
        params.append(query.jurisdiction)

    if query.date_from:
        param_count += 1
        sql += f" AND c.decision_date >= ${param_count}"
        params.append(query.date_from)

    if query.date_to:
        param_count += 1
        sql += f" AND c.decision_date <= ${param_count}"
        params.append(query.date_to)

    sql += f"""
        ORDER BY score DESC
        LIMIT {query.limit}
    """

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    results = []
    for row in rows:
        court_name = row["court_name"] or "Unknown Court"
        metadata = row["metadata"] if row["metadata"] else {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        results.append({
            "id": row["id"],
            "title": row["title"],
            "court_name": court_name,
            "decision_date": row["decision_date"].isoformat() if row["decision_date"] else "",
            "reporter_cite": row["reporter_cite"] or "",
            "content": row["content"][:500] if row["content"] else "",
            "citation_count": row["citation_count"],
            "score": float(row["score"])
        })

    return results

async def semantic_search(query: SearchQuery):
    """Semantic search using pgvector"""
    
    # Generate embedding for query
    embedding = await generate_embedding(query.query)

    # Format embedding as PostgreSQL vector string
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'

    # Search in PostgreSQL with pgvector - join with courts table and extract court from metadata
    sql = """
        SELECT
            cases.id, cases.title, cases.court_id, cases.decision_date,
            cases.reporter_cite, cases.content,
            courts.name as court_name,
            cases.metadata->>'court' as metadata_court,
            1 - (cases.embedding <=> $1::vector) as score
        FROM cases
        LEFT JOIN courts ON cases.court_id = courts.id
        WHERE 1=1
    """

    params = [embedding_str]
    param_count = 1

    if query.jurisdiction:
        param_count += 1
        sql += f" AND court_id = ${param_count}"
        params.append(query.jurisdiction)

    if query.date_from:
        param_count += 1
        sql += f" AND decision_date >= ${param_count}"
        params.append(query.date_from)

    if query.date_to:
        param_count += 1
        sql += f" AND decision_date <= ${param_count}"
        params.append(query.date_to)
    
    sql += f" ORDER BY embedding <=> $1::vector LIMIT {query.limit}"
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    
    results = []
    for row in rows:
        # Get court name from join, or fallback to metadata_court
        court_name = row["court_name"] or row["metadata_court"] or "Unknown Court"

        results.append({
            "id": row["id"],
            "title": row["title"],
            "court_name": court_name,  # Changed from "court" to "court_name" to match frontend
            "date": row["decision_date"].isoformat() if row["decision_date"] else "",
            "reporter_cite": row["reporter_cite"] or "",
            "content": row["content"][:500] if row["content"] else "",  # Truncate for response
            "score": float(row["score"])
        })

    return results

def reciprocal_rank_fusion(list1, list2, k=60):
    """Combine two ranked lists using RRF"""
    scores = {}
    
    for rank, item in enumerate(list1):
        case_id = item.get("id") or item.get("case_id")
        scores[case_id] = scores.get(case_id, 0) + 1 / (k + rank + 1)
    
    for rank, item in enumerate(list2):
        case_id = item.get("id") or item.get("case_id")
        scores[case_id] = scores.get(case_id, 0) + 1 / (k + rank + 1)
    
    # Create merged list
    case_map = {}
    for item in list1 + list2:
        case_id = item.get("id") or item.get("case_id")
        if case_id not in case_map:
            case_map[case_id] = item
    
    # Sort by RRF score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    results = []
    for case_id in sorted_ids[:10]:  # Top 10
        case = case_map[case_id]
        case["score"] = scores[case_id]
        results.append(case)
    
    return results

async def generate_embedding(text: str):
    """Generate embeddings using OpenAI API"""

    # Check cache (if Redis available)
    cache_key = f"embedding:{hash(text)}"
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"input": text, "model": "text-embedding-3-small"}
        )
    
    embedding = response.json()["data"][0]["embedding"]

    # Cache embedding (if Redis available)
    if redis_client:
        try:
            await redis_client.setex(cache_key, 86400, json.dumps(embedding))
        except:
            pass

    return embedding

@app.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str):
    """Get a specific case by ID"""

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT c.*, ct.name as court_name
               FROM cases c
               LEFT JOIN courts ct ON c.court_id = ct.id
               WHERE c.id = $1""",
            case_id
        )

    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    result = dict(row)

    # Add stub indicator
    result["is_stub"] = not result.get("content")

    # Parse metadata if it's a JSON string
    if result.get("metadata") and isinstance(result["metadata"], str):
        try:
            result["metadata"] = json.loads(result["metadata"])
        except json.JSONDecodeError:
            result["metadata"] = {}

    # Try to get full opinion text from metadata
    if result.get("metadata") and isinstance(result["metadata"], dict):
        opinions = result["metadata"].get("opinions", [])
        if opinions:
            opinion = opinions[0]

            # Store PDF URL if available
            download_url = opinion.get("download_url")
            if download_url:
                result["pdf_url"] = download_url

            # Use the snippet from metadata if it's longer than current content
            # The snippet often contains the beginning of the full opinion
            snippet = opinion.get("snippet", "")
            if snippet and len(snippet) > len(result.get("content", "")):
                result["content"] = snippet
                result["content_type"] = "plain_text"

    return result

@app.get("/api/v1/cases/{case_id}/citations")
async def get_case_citations(case_id: str):
    """Get all cases that cite this case and cases this case cites"""

    async with db_pool.acquire() as conn:
        # Get cases that cite this case (citing_cases)
        citing = await conn.fetch(
            """
            SELECT c.id, c.title, c.decision_date, ct.name as court_name,
                   cit.signal, cit.context_span as snippet
            FROM citations cit
            JOIN cases c ON cit.source_case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cit.target_case_id = $1
            ORDER BY c.decision_date DESC NULLS LAST
            """,
            case_id
        )

        # Get cases that this case cites (cited_cases)
        cited = await conn.fetch(
            """
            SELECT c.id, c.title, c.decision_date, ct.name as court_name,
                   cit.signal, cit.context_span as snippet
            FROM citations cit
            JOIN cases c ON cit.target_case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cit.source_case_id = $1
            ORDER BY c.decision_date DESC NULLS LAST
            """,
            case_id
        )

        return {
            "case_id": case_id,
            "citing_cases": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "decision_date": r["decision_date"].isoformat() if r["decision_date"] else None,
                    "court_name": r["court_name"],
                    "signal": r["signal"],
                    "snippet": r["snippet"]
                }
                for r in citing
            ],
            "cited_cases": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "decision_date": r["decision_date"].isoformat() if r["decision_date"] else None,
                    "court_name": r["court_name"],
                    "signal": r["signal"],
                    "snippet": r["snippet"]
                }
                for r in cited
            ],
            "citing_count": len(citing),
            "cited_count": len(cited)
        }

@app.get("/api/v1/cases/{case_id}/citator")
async def get_citator(case_id: str):
    """Get citator information for a case"""

    async with db_pool.acquire() as conn:
        # Get citing cases
        citing = await conn.fetch(
            """
            SELECT c2.*, ct.signal, ct.snippet
            FROM citations ct
            JOIN cases c2 ON ct.source_case_id = c2.id
            WHERE ct.target_case_id = $1
            ORDER BY c2.decision_date DESC NULLS LAST
            LIMIT 100
            """,
            case_id
        )
        
        # Analyze treatments
        negative = []
        positive = []
        
        for row in citing:
            case_dict = dict(row)
            if row["signal"] in ["overruled", "criticized", "questioned"]:
                negative.append(case_dict)
            elif row["signal"] in ["followed", "affirmed", "cited_favorably"]:
                positive.append(case_dict)
        
        # Determine badge
        if len(negative) > 0:
            badge = "red" if any(c["signal"] == "overruled" for c in negative) else "yellow"
        else:
            badge = "green"
        
        return CitatorResult(
            case_id=case_id,
            badge=badge,
            citing_cases=[dict(r) for r in citing[:10]],
            negative_treatments=negative[:5],
            positive_treatments=positive[:5]
        )

@app.get("/api/v1/cases/{case_id}/summary")
async def get_case_summary(case_id: str, user: Optional[dict] = Depends(get_current_user)):
    """Get cached AI summary if it exists, with rating info"""
    async with db_pool.acquire() as conn:
        cached = await conn.fetchrow(
            """
            SELECT summary, model, input_tokens, output_tokens, cost, created_at
            FROM ai_summaries
            WHERE case_id = $1
            """,
            case_id
        )

        # Get aggregate ratings (graceful if table missing)
        ratings = {"thumbs_up": 0, "thumbs_down": 0, "user_rating": None}
        try:
            rating_row = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as thumbs_up,
                    COALESCE(SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END), 0) as thumbs_down
                FROM public.summary_ratings WHERE case_id = $1
            """, case_id)

            if rating_row:
                ratings["thumbs_up"] = rating_row["thumbs_up"]
                ratings["thumbs_down"] = rating_row["thumbs_down"]

            # Get user's own rating if logged in
            if user:
                ur = await conn.fetchrow(
                    "SELECT rating FROM public.summary_ratings WHERE case_id = $1 AND user_id = $2",
                    case_id, user["id"]
                )
                if ur:
                    ratings["user_rating"] = ur["rating"]
        except Exception as e:
            print(f"Warning: summary_ratings query failed: {e}")

        if not cached:
            return {"summary": None, "cached": False, "ratings": ratings}

        # Get citing and cited cases for the response
        citing_query = await conn.fetch(
            """
            SELECT c.id, c.title, c.decision_date, ct.name as court_name
            FROM citations cit
            JOIN cases c ON cit.source_case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cit.target_case_id = $1
            LIMIT 5
            """,
            case_id
        )

        cited_query = await conn.fetch(
            """
            SELECT c.id, c.title, c.decision_date, ct.name as court_name
            FROM citations cit
            JOIN cases c ON cit.target_case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cit.source_case_id = $1
            LIMIT 5
            """,
            case_id
        )

        return {
            "summary": cached["summary"],
            "cost": float(cached["cost"]) if cached["cost"] else 0,
            "citing_cases": [dict(r) for r in citing_query],
            "cited_cases": [dict(r) for r in cited_query],
            "tokens_used": {
                "input": cached["input_tokens"],
                "output": cached["output_tokens"],
                "total": cached["input_tokens"] + cached["output_tokens"]
            },
            "cached": True,
            "cached_at": cached["created_at"].isoformat() if cached["created_at"] else None,
            "model": cached["model"],
            "ratings": ratings,
        }


@app.post("/api/v1/cases/{case_id}/summary/rate")
async def rate_summary(case_id: str, data: SummaryRating, user: dict = Depends(require_auth)):
    """Rate an AI summary thumbs up (+1) or down (-1). Send 0 to remove rating."""
    if data.rating not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="Rating must be -1, 0, or 1")

    try:
        async with db_pool.acquire() as conn:
            if data.rating == 0:
                # Remove existing rating
                await conn.execute(
                    "DELETE FROM public.summary_ratings WHERE case_id = $1 AND user_id = $2",
                    case_id, str(user["id"])
                )
            else:
                # Upsert rating
                await conn.execute("""
                    INSERT INTO public.summary_ratings (case_id, user_id, rating, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (case_id, user_id) DO UPDATE SET rating = EXCLUDED.rating, updated_at = NOW()
                """, case_id, str(user["id"]), int(data.rating))

            # Return aggregate counts
            agg = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END), 0) as thumbs_up,
                    COALESCE(SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END), 0) as thumbs_down
                FROM public.summary_ratings WHERE case_id = $1
            """, case_id)

            # Get user's current rating
            ur = await conn.fetchrow(
                "SELECT rating FROM public.summary_ratings WHERE case_id = $1 AND user_id = $2",
                case_id, str(user["id"])
            )

        return {
            "thumbs_up": agg["thumbs_up"],
            "thumbs_down": agg["thumbs_down"],
            "user_rating": ur["rating"] if ur else None,
        }
    except Exception as e:
        print(f"Error in rate_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/cases/{case_id}/summarize")
async def summarize_case(case_id: str, authorization: Optional[str] = Header(None)):
    """Generate an AI-powered case brief summary"""

    # Try to get user for BYOK
    current_user = await get_current_user(authorization)
    user_id = current_user["id"] if current_user else None
    api_key, key_source = await get_anthropic_api_key(user_id)

    # Check community pool for non-BYOK users
    if key_source == "site":
        if not await check_pool_available(user_id):
            raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)

    # Get the case from database and related cases
    async with db_pool.acquire() as conn:
        # Check if we already have a cached summary
        cached = await conn.fetchrow(
            """
            SELECT summary, model, input_tokens, output_tokens, cost, created_at
            FROM ai_summaries
            WHERE case_id = $1
            """,
            case_id
        )
        row = await conn.fetchrow(
            """
            SELECT c.*, ct.name as court_name
            FROM cases c
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE c.id = $1
            """,
            case_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Case not found")

        # Get citing and cited cases for context
        citing_query = await conn.fetch(
            """
            SELECT c.id, c.title, c.decision_date, ct.name as court_name
            FROM citations cit
            JOIN cases c ON cit.source_case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cit.target_case_id = $1
            LIMIT 5
            """,
            case_id
        )

        cited_query = await conn.fetch(
            """
            SELECT c.id, c.title, c.decision_date, ct.name as court_name
            FROM citations cit
            JOIN cases c ON cit.target_case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cit.source_case_id = $1
            LIMIT 5
            """,
            case_id
        )

        # Return cached summary if it exists
        if cached:
            print(f"✅ Returning cached summary for case {case_id}")
            return {
                "summary": cached["summary"],
                "cost": float(cached["cost"]) if cached["cost"] else 0,
                "citing_cases": [dict(r) for r in citing_query],
                "cited_cases": [dict(r) for r in cited_query],
                "tokens_used": {
                    "input": cached["input_tokens"],
                    "output": cached["output_tokens"],
                    "total": cached["input_tokens"] + cached["output_tokens"]
                },
                "cached": True,
                "cached_at": cached["created_at"].isoformat() if cached["created_at"] else None,
                "model": cached["model"]
            }

    case_data = dict(row)
    is_stub = not case_data.get("content")

    # Stub cases require authentication (cost protection)
    if is_stub:
        user = await get_current_user(authorization)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Sign in to generate briefs for cases not yet in our database"
            )

        # Fetch opinion text from CourtListener API
        cluster_id = case_id
        print(f"Fetching opinion from CourtListener for stub case {cluster_id}...")

        fetched_content = None
        cl_token = os.getenv('COURTLISTENER_API_KEY', '')
        cl_headers = {"Authorization": f"Token {cl_token}"} if cl_token else {}

        def extract_text_from_opinion(opinion_data: dict) -> str:
            """Extract plain text from a CourtListener opinion response."""
            from bs4 import BeautifulSoup as BS4
            # Try plain text first
            if opinion_data.get("plain_text") and len(opinion_data["plain_text"]) > 100:
                return opinion_data["plain_text"]
            # Try HTML fields in order of preference
            for field in ["html_lawbox", "html_with_citations", "html", "html_columbia", "xml_harvard"]:
                html_content = opinion_data.get(field, "")
                if html_content:
                    soup = BS4(html_content, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                    if len(text) > 100:
                        return text
            return ""

        try:
            async with httpx.AsyncClient() as client:
                # Strategy 1: Get cluster → find opinion IDs → fetch opinion text
                if cl_headers:
                    cluster_resp = await client.get(
                        f"https://www.courtlistener.com/api/rest/v4/clusters/{cluster_id}/",
                        headers=cl_headers,
                        timeout=30.0,
                    )
                    if cluster_resp.status_code == 200:
                        cluster_data = cluster_resp.json()
                        opinion_urls = cluster_data.get("sub_opinions", [])

                        for opinion_url in opinion_urls:
                            opinion_id = opinion_url.rstrip("/").split("/")[-1]
                            opinion_resp = await client.get(
                                f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/",
                                headers=cl_headers,
                                timeout=30.0,
                            )
                            if opinion_resp.status_code == 200:
                                text = extract_text_from_opinion(opinion_resp.json())
                                if len(text) > 500:
                                    fetched_content = text
                                    print(f"  Got {len(text)} chars via cluster sub_opinions")
                                    break
                    else:
                        print(f"  Cluster API returned {cluster_resp.status_code}")

                # Strategy 2: Try fetching opinion directly by cluster ID
                if not fetched_content:
                    opinion_resp = await client.get(
                        f"https://www.courtlistener.com/api/rest/v4/opinions/{cluster_id}/",
                        headers=cl_headers,
                        timeout=30.0,
                    )
                    if opinion_resp.status_code == 200:
                        text = extract_text_from_opinion(opinion_resp.json())
                        if len(text) > 500:
                            fetched_content = text
                            print(f"  Got {len(text)} chars via direct opinion fetch")

                # Strategy 3: Search for opinions by cluster (handles mismatched IDs)
                if not fetched_content and cl_headers:
                    search_resp = await client.get(
                        f"https://www.courtlistener.com/api/rest/v4/opinions/",
                        params={"cluster": cluster_id},
                        headers=cl_headers,
                        timeout=30.0,
                    )
                    if search_resp.status_code == 200:
                        results = search_resp.json().get("results", [])
                        for result in results:
                            text = extract_text_from_opinion(result)
                            if len(text) > 500:
                                fetched_content = text
                                print(f"  Got {len(text)} chars via opinions search")
                                break

        except Exception as e:
            print(f"Error fetching from CourtListener: {e}")

        if not fetched_content:
            raise HTTPException(
                status_code=404,
                detail="Could not fetch opinion text from CourtListener. The full opinion may not be available electronically."
            )

        # Save fetched content to database ("graduate" the stub)
        async with db_pool.acquire() as conn:
            # Update content and remove stub flag from metadata
            metadata = case_data.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    metadata = {}
            if isinstance(metadata, dict):
                metadata.pop("stub", None)

            await conn.execute(
                """
                UPDATE cases SET content = $1, metadata = $2, updated_at = NOW()
                WHERE id = $3
                """,
                fetched_content,
                json.dumps(metadata) if metadata else None,
                case_id,
            )
            print(f"Saved {len(fetched_content)} chars of opinion text for case {case_id}")

        # Update case_data with the fetched content for summary generation
        case_data["content"] = fetched_content

    # Parse metadata if it's a JSON string
    if case_data.get("metadata") and isinstance(case_data["metadata"], str):
        try:
            case_data["metadata"] = json.loads(case_data["metadata"])
        except json.JSONDecodeError:
            case_data["metadata"] = {}

    # Get case content - try PDF first, then fallback to database content
    content = ""
    pdf_url = None

    # Check if we have a PDF URL in metadata
    if case_data.get("metadata") and isinstance(case_data["metadata"], dict):
        opinions = case_data["metadata"].get("opinions", [])
        if opinions:
            pdf_url = opinions[0].get("download_url")

    # Try to extract text from PDF
    if pdf_url:
        try:
            print(f"Fetching PDF from: {pdf_url}")
            import io
            import pdfplumber

            async with httpx.AsyncClient() as client:
                pdf_response = await client.get(pdf_url, timeout=30.0, follow_redirects=True)

                if pdf_response.status_code == 200:
                    # Extract text from PDF
                    pdf_file = io.BytesIO(pdf_response.content)
                    with pdfplumber.open(pdf_file) as pdf:
                        pdf_text = ""
                        # Extract from first 15 pages (usually enough for a case)
                        for page in pdf.pages[:15]:
                            pdf_text += page.extract_text() or ""

                        if len(pdf_text) > 500:
                            content = pdf_text
                            print(f"✅ Extracted {len(content)} characters from PDF")
                        else:
                            print(f"⚠️ PDF text too short ({len(pdf_text)} chars), using database content")
        except Exception as e:
            print(f"⚠️ Failed to extract PDF text: {e}")

    # Fallback to database content if PDF extraction failed
    if not content:
        content = case_data.get("content", "")
        print(f"Using database content: {len(content)} characters")

        # Strip HTML tags if present
        import re
        if '<' in content and '>' in content:
            content = re.sub('<.*?>', '', content)
            content = ' '.join(content.split())

    # Limit to 20,000 characters for API cost management
    # (GPT-4o-mini is cheap enough to handle more text)
    if len(content) > 20000:
        # Take first 18000 and last 2000 to get beginning and conclusion
        content = content[:18000] + "\n\n[...middle section omitted...]\n\n" + content[-2000:]
        print(f"Truncated content to 20,000 characters (with middle section omitted)")

    # Prepare prompt for GPT
    case_name = case_data.get("title") or case_data.get("case_name", "Unknown Case")
    court = case_data.get("court_name") or case_data.get("court_id", "Unknown Court")
    date = case_data.get("decision_date") or case_data.get("date_filed")
    date_str = date.isoformat() if date else "Unknown Date"

    prompt = f"""You are a legal research assistant. Analyze this case opinion and provide a comprehensive brief.

**Case Information:**
- Name: {case_name}
- Court: {court}
- Date: {date_str}

**Full Case Opinion:**
{content}

Please provide a structured legal brief with these sections:

**📋 Facts**
Summarize the key facts in 4-5 sentences. Include the parties involved, what happened that led to this lawsuit, and the procedural history. Focus on facts that are crucial to understanding the legal issues.

**⚖️ Issue(s)**
State the legal question(s) the court had to decide. Be specific and frame as questions. If there are multiple issues, number them.

**📚 Holding**
State the court's decision clearly and completely. What did the court rule on each issue? Include the outcome (affirmed, reversed, remanded, etc.).

**💡 Reasoning**
Explain the court's rationale in 4-6 sentences. Why did they decide this way? What legal principles, statutes, or precedents did they rely on? Include key quotes or citations if particularly important.

**🎯 Significance**
Why does this case matter? How might it be used in legal practice? What legal principle does it establish or clarify? (3-4 sentences)

Format your response with clear section headers using the emoji markers shown above. Be thorough and specific, using the full opinion text provided.
"""

    try:
        # Call Anthropic Messages API with Claude Sonnet 4.6
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                timeout=90.0  # Increased timeout for longer cases
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Anthropic API error: {response.text}"
            )

        result = response.json()
        print(f"Claude API Response: stop_reason={result.get('stop_reason')}")  # Debug logging

        # Extract text from Claude's response
        content_blocks = result.get("content", [])
        summary = None

        for block in content_blocks:
            if block.get("type") == "text":
                summary = block.get("text")
                break

        if not summary:
            print(f"Could not find text in response. Content blocks: {len(content_blocks)}")
            raise HTTPException(
                status_code=500,
                detail="Could not extract text from Claude response"
            )

        # Calculate cost
        # Claude Sonnet 4.6: $3 per 1M input tokens, $15 per 1M output tokens
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

        # Save the summary to database for caching (benefits everyone)
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ai_summaries (case_id, summary, model, input_tokens, output_tokens, cost)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (case_id) DO UPDATE
                SET summary = EXCLUDED.summary,
                    model = EXCLUDED.model,
                    input_tokens = EXCLUDED.input_tokens,
                    output_tokens = EXCLUDED.output_tokens,
                    cost = EXCLUDED.cost,
                    created_at = CURRENT_TIMESTAMP
                """,
                case_id, summary, "claude-sonnet-4-6", input_tokens, output_tokens, cost
            )

        print(f"💾 Saved summary for case {case_id} to database")

        # Log usage for transparency dashboard
        await log_api_usage("ai_summary", input_tokens, output_tokens, cost, source=key_source)

        return {
            "summary": summary,
            "cost": cost,
            "citing_cases": [dict(r) for r in citing_query],
            "cited_cases": [dict(r) for r in cited_query],
            "tokens_used": {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens
            },
            "cached": False,
            "model": "claude-sonnet-4-6"
        }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI service timeout")
    except Exception as e:
        print(f"Error generating summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/briefcheck")
async def check_brief(file: UploadFile = File(...)):
    """Analyze a brief for missing authorities and treatments"""
    
    # Read file content
    content = await file.read()
    
    # Extract text based on file type
    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(content)
    elif file.filename.endswith(".docx"):
        text = extract_text_from_docx(content)
    else:
        text = content.decode("utf-8")
    
    # Extract citations from brief
    citations = await extract_citations(text)
    
    # Check each citation
    results = {
        "total_citations": len(citations),
        "negative_treatments": [],
        "missing_authorities": [],
        "suggested_cases": []
    }
    
    for cite in citations:
        # Look up case
        case = await find_case_by_citation(cite)
        if case:
            # Check treatment
            citator = await get_citator(case["id"])
            if citator.badge in ["red", "yellow"]:
                results["negative_treatments"].append({
                    "citation": cite,
                    "case": case,
                    "badge": citator.badge,
                    "treatments": citator.negative_treatments
                })
    
    # Find missing authorities using semantic search
    key_passages = extract_key_arguments(text)
    for passage in key_passages:
        similar_cases = await semantic_search(
            SearchQuery(query=passage, limit=5)
        )
        
        # Filter out already cited cases
        for case in similar_cases:
            if case["id"] not in [c["id"] for c in citations]:
                results["suggested_cases"].append(case)
    
    return results


@app.get("/api/v1/transparency")
async def get_transparency_stats():
    """Get transparency dashboard statistics for public display"""
    import calendar

    async with db_pool.acquire() as conn:
        # Current month stats from api_usage_log
        month_stats = await conn.fetchrow("""
            SELECT COALESCE(SUM(call_count), 0) as summaries,
                   COALESCE(SUM(estimated_cost), 0) as cost
            FROM api_usage_log
            WHERE usage_type = 'ai_summary'
            AND DATE_TRUNC('month', usage_date) = DATE_TRUNC('month', CURRENT_DATE)
        """)

        # All-time stats from api_usage_log
        alltime = await conn.fetchrow("""
            SELECT COALESCE(SUM(call_count), 0) as summaries,
                   COALESCE(SUM(estimated_cost), 0) as cost
            FROM api_usage_log
            WHERE usage_type = 'ai_summary'
        """)

        # Fallback to ai_summaries table if no usage logged yet
        if alltime["summaries"] == 0:
            fallback = await conn.fetchrow("""
                SELECT COUNT(*) as summaries, COALESCE(SUM(cost), 0) as cost
                FROM ai_summaries
            """)
            alltime_summaries = fallback["summaries"]
            alltime_cost = float(fallback["cost"]) if fallback["cost"] else 0
        else:
            alltime_summaries = alltime["summaries"]
            alltime_cost = float(alltime["cost"])

        # Get config values from site_config table
        config_rows = await conn.fetch("SELECT key, value FROM site_config")
        config = {row["key"]: row["value"] for row in config_rows}

        # Get donations from donations table (from Ko-fi webhooks)
        month_donations = await conn.fetchrow("""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
            FROM donations
            WHERE DATE_TRUNC('month', received_at) = DATE_TRUNC('month', CURRENT_DATE)
        """)

        alltime_donations = await conn.fetchrow("""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count
            FROM donations
        """)

    # Parse config values with defaults
    hosting = float(config.get("monthly_hosting_cost", "5.00"))
    goal = float(config.get("monthly_goal", "25.00"))
    donations = float(month_donations["total"]) if month_donations else 0
    donations_count = month_donations["count"] if month_donations else 0
    total_donations = float(alltime_donations["total"]) if alltime_donations else 0

    month_ai_cost = float(month_stats["cost"]) if month_stats["cost"] else 0
    month_total = month_ai_cost + hosting

    # Community pool: real balance from pool_ledger
    try:
        pool_balance = await get_pool_balance()
    except Exception:
        pool_balance = 0.0
    low_threshold = float(config.get("pool_low_threshold", "5.00"))
    community_pool_balance = round(pool_balance, 2)
    community_pool_healthy = pool_balance > 0
    community_pool_low = pool_balance > 0 and pool_balance < low_threshold

    return {
        "month_name": calendar.month_name[datetime.now().month],
        "month_summaries": month_stats["summaries"] if month_stats else 0,
        "month_ai_cost": round(month_ai_cost, 2),
        "month_hosting_cost": hosting,
        "month_total_cost": round(month_total, 2),
        "monthly_donations": round(donations, 2),
        "monthly_donations_count": donations_count,
        "total_donations": round(total_donations, 2),
        "total_summaries": alltime_summaries,
        "total_ai_cost": round(alltime_cost, 2),
        "monthly_goal": goal,
        "goal_percent": min(100, round((month_total / goal) * 100, 1)) if goal > 0 else 0,
        "kofi_url": f"https://ko-fi.com/{config.get('kofi_username', '')}" if config.get('kofi_username') else "",
        "charity_name": config.get("charity_name", "Houseless Movement"),
        "charity_description": config.get("charity_description", ""),
        "charity_url": config.get("charity_url", ""),
        "community_pool_balance": max(0, community_pool_balance),
        "community_pool_healthy": community_pool_healthy,
        "community_pool_low": community_pool_low,
    }


@app.get("/api/v1/sitemap/cases")
async def get_sitemap_cases():
    """Get all case IDs and titles for sitemap generation"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, decision_date
            FROM cases
            ORDER BY decision_date DESC NULLS LAST
        """)

    return {
        "cases": [
            {
                "id": row["id"],
                "title": row["title"],
                "date": row["decision_date"].isoformat() if row["decision_date"] else None
            }
            for row in rows
        ],
        "count": len(rows)
    }


@app.post("/api/v1/kofi-webhook")
async def kofi_webhook(data: str = Form(...)):
    """
    Receive Ko-fi donation webhooks.
    Ko-fi sends POST with content-type application/x-www-form-urlencoded
    and a 'data' field containing JSON.
    """
    try:
        # Parse the JSON data from the form field
        payload = json.loads(data)

        # Extract donation info
        transaction_id = payload.get("kofi_transaction_id")
        amount = float(payload.get("amount", 0))
        from_name = payload.get("from_name", "Anonymous")
        message = payload.get("message")
        donation_type = payload.get("type", "Donation")
        is_public = payload.get("is_public", True)
        is_subscription = payload.get("is_subscription_payment", False)
        tier_name = payload.get("tier_name")

        # Store in database
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO donations (
                    kofi_transaction_id, from_name, message, amount,
                    donation_type, is_public, is_subscription, tier_name, raw_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (kofi_transaction_id) DO NOTHING
            """,
                transaction_id, from_name, message, amount,
                donation_type, is_public, is_subscription, tier_name,
                json.dumps(payload)
            )

        # Credit the community pool
        await credit_pool(amount, "donation", f"Ko-fi from {from_name}", transaction_id, "kofi")

        print(f"☕ Ko-fi donation received: ${amount} from {from_name}")

        # Return 200 as Ko-fi expects
        return {"status": "success"}

    except Exception as e:
        print(f"❌ Ko-fi webhook error: {e}")
        # Still return 200 to prevent retries for malformed data
        return {"status": "error", "message": str(e)}


async def extract_citations(text: str):
    """Extract legal citations from text using Eyecite"""
    # This would use the Eyecite library in production
    # Simplified regex for demo
    import re
    
    patterns = [
        r'\d+\s+F\.\d+\s+\d+',  # Federal Reporter
        r'\d+\s+U\.S\.\s+\d+',  # US Reports
        r'\d+\s+S\.\s?Ct\.\s+\d+',  # Supreme Court Reporter
    ]
    
    citations = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        citations.extend(matches)
    
    return citations

async def find_case_by_citation(citation: str):
    """Find a case by its reporter citation"""
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM cases WHERE reporter_cite = $1",
            citation
        )
    
    return dict(row) if row else None

def extract_key_arguments(text: str, max_passages=5):
    """Extract key argument passages from brief"""
    # Simplified - would use NLP in production
    sentences = text.split(". ")
    
    # Look for argument indicators
    key_sentences = []
    for sent in sentences:
        if any(indicator in sent.lower() for indicator in 
               ["argue", "contend", "maintain", "assert", "claim"]):
            key_sentences.append(sent)
    
    return key_sentences[:max_passages]

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF using pdfplumber"""
    import pdfplumber
    text = ""
    pdf_file = io.BytesIO(content)
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX using python-docx"""
    from docx import Document
    doc_file = io.BytesIO(content)
    doc = Document(doc_file)
    text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    return text.strip()


# ============================================================================
# Library Feature Endpoints
# ============================================================================

@app.get("/api/v1/library/collections")
async def list_collections(user: dict = Depends(require_auth)):
    """List all collections for the authenticated user"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.id, c.name, c.description, c.subject, c.is_public, c.created_at,
                   COUNT(DISTINCT cc.id) as case_count,
                   COUNT(DISTINCT clt.id) as legal_text_count
            FROM collections c
            LEFT JOIN collection_cases cc ON c.id = cc.collection_id
            LEFT JOIN collection_legal_texts clt ON c.id = clt.collection_id
            WHERE c.user_id = $1
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """, user["id"])

    return {
        "collections": [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"],
                "subject": row["subject"],
                "is_public": row["is_public"],
                "case_count": row["case_count"],
                "legal_text_count": row["legal_text_count"],
                "item_count": row["case_count"] + row["legal_text_count"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            for row in rows
        ]
    }


@app.post("/api/v1/library/collections")
async def create_collection(collection: CollectionCreate, user: dict = Depends(require_auth)):
    """Create a new collection"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO collections (user_id, name, description, subject, is_public)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, description, subject, is_public, created_at
        """, user["id"], collection.name, collection.description, collection.subject, collection.is_public)

    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "subject": row["subject"],
        "is_public": row["is_public"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None
    }


@app.get("/api/v1/library/collections/{collection_id}")
async def get_collection(collection_id: str, user: dict = Depends(require_auth)):
    """Get a collection with its cases"""
    # Convert collection_id to integer (DB uses SERIAL)
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        # Get collection info
        collection = await conn.fetchrow("""
            SELECT id, user_id, name, description, subject, is_public, created_at
            FROM collections
            WHERE id = $1 AND user_id = $2
        """, coll_id, user["id"])

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Get cases in collection
        cases = await conn.fetch("""
            SELECT cc.id as collection_case_id, cc.notes, cc.added_at, cc.position,
                   c.id, c.title, c.decision_date, c.reporter_cite,
                   ct.name as court_name
            FROM collection_cases cc
            JOIN cases c ON cc.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cc.collection_id = $1
            ORDER BY cc.position ASC, cc.added_at DESC
        """, coll_id)

        # Get legal texts in collection
        legal_texts = await conn.fetch("""
            SELECT clt.id as collection_lt_id, clt.notes, clt.added_at, clt.position,
                   i.id as item_id, i.document_id, i.slug, i.title, i.citation, i.number
            FROM collection_legal_texts clt
            JOIN legal_text_items i ON clt.legal_text_item_id = i.id
            WHERE clt.collection_id = $1
            ORDER BY clt.position ASC, clt.added_at DESC
        """, coll_id)

    return {
        "id": str(collection["id"]),
        "name": collection["name"],
        "description": collection["description"],
        "subject": collection["subject"],
        "is_public": collection["is_public"],
        "created_at": collection["created_at"].isoformat() if collection["created_at"] else None,
        "cases": [
            {
                "collection_case_id": str(c["collection_case_id"]),
                "id": c["id"],
                "title": c["title"],
                "decision_date": c["decision_date"].isoformat() if c["decision_date"] else None,
                "reporter_cite": c["reporter_cite"],
                "court_name": c["court_name"],
                "notes": c["notes"],
                "added_at": c["added_at"].isoformat() if c["added_at"] else None,
                "position": c["position"] if c["position"] is not None else 0
            }
            for c in cases
        ],
        "legal_texts": [
            {
                "collection_lt_id": str(lt["collection_lt_id"]),
                "item_id": lt["item_id"],
                "document_id": lt["document_id"],
                "slug": lt["slug"],
                "title": lt["title"],
                "citation": lt["citation"],
                "number": lt["number"],
                "notes": lt["notes"],
                "added_at": lt["added_at"].isoformat() if lt["added_at"] else None,
                "position": lt["position"] if lt["position"] is not None else 0
            }
            for lt in legal_texts
        ]
    }


@app.put("/api/v1/library/collections/{collection_id}")
async def update_collection(collection_id: str, update: CollectionUpdate, user: dict = Depends(require_auth)):
    """Update a collection"""
    # Convert collection_id to integer (DB uses SERIAL)
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    # Build dynamic update query
    updates = []
    params = [coll_id, user["id"]]
    param_idx = 3

    if update.name is not None:
        updates.append(f"name = ${param_idx}")
        params.append(update.name)
        param_idx += 1

    if update.description is not None:
        updates.append(f"description = ${param_idx}")
        params.append(update.description)
        param_idx += 1

    if update.subject is not None:
        updates.append(f"subject = ${param_idx}")
        params.append(update.subject)
        param_idx += 1

    if update.is_public is not None:
        updates.append(f"is_public = ${param_idx}")
        params.append(update.is_public)
        param_idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(f"""
            UPDATE collections
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1 AND user_id = $2
            RETURNING id, name, description, subject, is_public, created_at
        """, *params)

    if not row:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row["description"],
        "subject": row["subject"],
        "is_public": row["is_public"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None
    }


@app.delete("/api/v1/library/collections/{collection_id}")
async def delete_collection(collection_id: str, user: dict = Depends(require_auth)):
    """Delete a collection"""
    # Convert collection_id to integer (DB uses SERIAL)
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM collections
            WHERE id = $1 AND user_id = $2
        """, coll_id, user["id"])

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Collection not found")

    return {"status": "deleted"}


@app.post("/api/v1/library/collections/{collection_id}/cases")
async def add_case_to_collection(collection_id: str, data: AddCaseToCollection, user: dict = Depends(require_auth)):
    """Add a case to a collection"""
    # Convert collection_id to integer (DB uses SERIAL)
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        # Verify collection ownership
        collection = await conn.fetchrow("""
            SELECT id FROM collections WHERE id = $1 AND user_id = $2
        """, coll_id, user["id"])

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Verify case exists
        case = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", data.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Add to collection (ignore if already exists)
        try:
            # Compute next position across both tables
            max_pos = await conn.fetchval("""
                SELECT COALESCE(MAX(pos), -1) FROM (
                    SELECT position AS pos FROM collection_cases WHERE collection_id = $1
                    UNION ALL
                    SELECT position AS pos FROM collection_legal_texts WHERE collection_id = $1
                ) sub
            """, coll_id)
            next_pos = (max_pos or 0) + 1

            row = await conn.fetchrow("""
                INSERT INTO collection_cases (collection_id, case_id, notes, position)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (collection_id, case_id) DO UPDATE SET notes = $3
                RETURNING id, added_at
            """, coll_id, data.case_id, data.notes, next_pos)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {
        "collection_case_id": str(row["id"]),
        "added_at": row["added_at"].isoformat() if row["added_at"] else None
    }


@app.delete("/api/v1/library/collections/{collection_id}/cases/{case_id}")
async def remove_case_from_collection(collection_id: str, case_id: str, user: dict = Depends(require_auth)):
    """Remove a case from a collection"""
    # Convert collection_id to integer (DB uses SERIAL)
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        # Verify collection ownership
        collection = await conn.fetchrow("""
            SELECT id FROM collections WHERE id = $1 AND user_id = $2
        """, coll_id, user["id"])

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        result = await conn.execute("""
            DELETE FROM collection_cases
            WHERE collection_id = $1 AND case_id = $2
        """, coll_id, case_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Case not in collection")

    return {"status": "removed"}


@app.post("/api/v1/library/collections/{collection_id}/legal-texts")
async def add_legal_text_to_collection(collection_id: str, data: AddLegalTextToCollection, user: dict = Depends(require_auth)):
    """Add a legal text to a collection"""
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        # Verify collection ownership
        collection = await conn.fetchrow("""
            SELECT id FROM collections WHERE id = $1 AND user_id = $2
        """, coll_id, user["id"])

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Verify legal text item exists
        item = await conn.fetchrow("SELECT id FROM legal_text_items WHERE id = $1", data.legal_text_item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Legal text item not found")

        # Add to collection (upsert)
        try:
            # Compute next position across both tables
            max_pos = await conn.fetchval("""
                SELECT COALESCE(MAX(pos), -1) FROM (
                    SELECT position AS pos FROM collection_cases WHERE collection_id = $1
                    UNION ALL
                    SELECT position AS pos FROM collection_legal_texts WHERE collection_id = $1
                ) sub
            """, coll_id)
            next_pos = (max_pos or 0) + 1

            row = await conn.fetchrow("""
                INSERT INTO collection_legal_texts (collection_id, legal_text_item_id, notes, position)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (collection_id, legal_text_item_id) DO UPDATE SET notes = $3
                RETURNING id, added_at
            """, coll_id, data.legal_text_item_id, data.notes, next_pos)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {
        "collection_lt_id": str(row["id"]),
        "added_at": row["added_at"].isoformat() if row["added_at"] else None
    }


@app.delete("/api/v1/library/collections/{collection_id}/legal-texts/{item_id}")
async def remove_legal_text_from_collection(collection_id: str, item_id: int, user: dict = Depends(require_auth)):
    """Remove a legal text from a collection"""
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        # Verify collection ownership
        collection = await conn.fetchrow("""
            SELECT id FROM collections WHERE id = $1 AND user_id = $2
        """, coll_id, user["id"])

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        result = await conn.execute("""
            DELETE FROM collection_legal_texts
            WHERE collection_id = $1 AND legal_text_item_id = $2
        """, coll_id, item_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Legal text not in collection")

    return {"status": "removed"}


@app.put("/api/v1/library/collections/{collection_id}/reorder")
async def reorder_collection_items(collection_id: str, data: ReorderRequest, user: dict = Depends(require_auth)):
    """Reorder items in a collection via drag-and-drop"""
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        # Verify collection ownership
        collection = await conn.fetchrow("""
            SELECT id FROM collections WHERE id = $1 AND user_id = $2
        """, coll_id, user["id"])

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Assign positions in a transaction
        async with conn.transaction():
            for idx, item in enumerate(data.items):
                if item.type == "case":
                    await conn.execute("""
                        UPDATE collection_cases
                        SET position = $1
                        WHERE collection_id = $2 AND case_id = $3
                    """, idx, coll_id, item.id)
                elif item.type == "legal_text":
                    try:
                        lt_item_id = int(item.id)
                    except ValueError:
                        continue
                    await conn.execute("""
                        UPDATE collection_legal_texts
                        SET position = $1
                        WHERE collection_id = $2 AND legal_text_item_id = $3
                    """, idx, coll_id, lt_item_id)

    return {"status": "ok"}


# ============================================================================
# Bookmarks Endpoints
# ============================================================================

@app.get("/api/v1/library/bookmarks")
async def list_bookmarks(user: dict = Depends(require_auth)):
    """List all bookmarks for the authenticated user"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT b.id, b.folder, b.notes, b.created_at,
                   c.id as case_id, c.title, c.decision_date, c.reporter_cite,
                   ct.name as court_name
            FROM bookmarks b
            JOIN cases c ON b.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE b.user_id = $1
            ORDER BY b.created_at DESC
        """, user["id"])

    return {
        "bookmarks": [
            {
                "id": str(row["id"]),
                "case_id": row["case_id"],
                "title": row["title"],
                "decision_date": row["decision_date"].isoformat() if row["decision_date"] else None,
                "reporter_cite": row["reporter_cite"],
                "court_name": row["court_name"],
                "folder": row["folder"],
                "notes": row["notes"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            for row in rows
        ]
    }


@app.post("/api/v1/library/bookmarks")
async def create_bookmark(bookmark: BookmarkCreate, user: dict = Depends(require_auth)):
    """Add a case to bookmarks"""
    async with db_pool.acquire() as conn:
        # Verify case exists
        case = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", bookmark.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        try:
            row = await conn.fetchrow("""
                INSERT INTO bookmarks (user_id, case_id, folder, notes)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, case_id) DO UPDATE SET folder = $3, notes = $4
                RETURNING id, created_at
            """, user["id"], bookmark.case_id, bookmark.folder, bookmark.notes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": str(row["id"]),
        "case_id": bookmark.case_id,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None
    }


@app.delete("/api/v1/library/bookmarks/{case_id}")
async def delete_bookmark(case_id: str, user: dict = Depends(require_auth)):
    """Remove a case from bookmarks"""
    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM bookmarks
            WHERE user_id = $1 AND case_id = $2
        """, user["id"], case_id)

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Bookmark not found")

    return {"status": "deleted"}


@app.get("/api/v1/library/bookmarks/check/{case_id}")
async def check_bookmark(case_id: str, user: dict = Depends(require_auth)):
    """Check if a case is bookmarked by the user"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id FROM bookmarks
            WHERE user_id = $1 AND case_id = $2
        """, user["id"], case_id)

    return {"bookmarked": row is not None}


# ============================================================================
# Shared Collections (Public)
# ============================================================================

@app.get("/api/v1/shared/{collection_id}")
async def get_shared_collection(collection_id: str):
    """Get a public shared collection (no auth required)"""
    # Convert collection_id to integer (DB uses SERIAL)
    try:
        coll_id = int(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID")

    async with db_pool.acquire() as conn:
        # Get collection info (must be public)
        collection = await conn.fetchrow("""
            SELECT c.id, c.name, c.description, c.subject, c.created_at,
                   p.full_name as owner_name
            FROM collections c
            LEFT JOIN profiles p ON c.user_id = p.id
            WHERE c.id = $1 AND c.is_public = true
        """, coll_id)

        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found or not public")

        # Get cases in collection
        cases = await conn.fetch("""
            SELECT cc.notes, cc.added_at, cc.position,
                   c.id, c.title, c.decision_date, c.reporter_cite,
                   ct.name as court_name
            FROM collection_cases cc
            JOIN cases c ON cc.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cc.collection_id = $1
            ORDER BY cc.position ASC, cc.added_at DESC
        """, coll_id)

        # Get legal texts in collection
        legal_texts = await conn.fetch("""
            SELECT clt.notes, clt.position,
                   i.id as item_id, i.document_id, i.slug, i.title, i.citation, i.number
            FROM collection_legal_texts clt
            JOIN legal_text_items i ON clt.legal_text_item_id = i.id
            WHERE clt.collection_id = $1
            ORDER BY clt.position ASC, clt.added_at DESC
        """, coll_id)

    return {
        "id": str(collection["id"]),
        "name": collection["name"],
        "description": collection["description"],
        "subject": collection["subject"],
        "owner_name": collection["owner_name"] or "Anonymous",
        "created_at": collection["created_at"].isoformat() if collection["created_at"] else None,
        "cases": [
            {
                "id": c["id"],
                "title": c["title"],
                "decision_date": c["decision_date"].isoformat() if c["decision_date"] else None,
                "reporter_cite": c["reporter_cite"],
                "court_name": c["court_name"],
                "notes": c["notes"],
                "position": c["position"] if c["position"] is not None else 0
            }
            for c in cases
        ],
        "legal_texts": [
            {
                "item_id": lt["item_id"],
                "document_id": lt["document_id"],
                "slug": lt["slug"],
                "title": lt["title"],
                "citation": lt["citation"],
                "number": lt["number"],
                "notes": lt["notes"],
                "position": lt["position"] if lt["position"] is not None else 0
            }
            for lt in legal_texts
        ],
        "case_count": len(cases),
        "legal_text_count": len(legal_texts),
        "item_count": len(cases) + len(legal_texts)
    }


# ============================================================================
# Profile
# ============================================================================

@app.get("/api/v1/profile")
async def get_own_profile(user: dict = Depends(require_auth)):
    """Get the current user's profile"""
    async with db_pool.acquire() as conn:
        profile = await conn.fetchrow("""
            SELECT id, username, full_name, avatar_url, bio, reputation,
                   law_school, graduation_year, is_public, created_at, updated_at
            FROM profiles WHERE id = $1
        """, user["id"])

        if not profile:
            # Create profile if doesn't exist
            profile = await conn.fetchrow("""
                INSERT INTO profiles (id, username, full_name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
                RETURNING id, username, full_name, avatar_url, bio, reputation,
                          law_school, graduation_year, is_public, created_at, updated_at
            """, user["id"], user.get("email", "").split("@")[0], user.get("email", "").split("@")[0])

            # Fetch again if ON CONFLICT triggered
            if not profile:
                profile = await conn.fetchrow("""
                    SELECT id, username, full_name, avatar_url, bio, reputation,
                           law_school, graduation_year, is_public, created_at, updated_at
                    FROM profiles WHERE id = $1
                """, user["id"])

    return {
        "id": profile["id"],
        "username": profile["username"],
        "full_name": profile["full_name"],
        "avatar_url": profile["avatar_url"],
        "bio": profile["bio"],
        "reputation": profile["reputation"] or 0,
        "law_school": profile["law_school"],
        "graduation_year": profile["graduation_year"],
        "is_public": profile["is_public"] or False,
        "email": user.get("email"),
        "created_at": profile["created_at"].isoformat() if profile["created_at"] else None,
        "updated_at": profile["updated_at"].isoformat() if profile["updated_at"] else None
    }


@app.put("/api/v1/profile")
async def update_profile(data: ProfileUpdate, user: dict = Depends(require_auth)):
    """Update the current user's profile"""
    async with db_pool.acquire() as conn:
        # Check if profile exists, create if not
        existing_profile = await conn.fetchrow(
            "SELECT id FROM profiles WHERE id = $1", user["id"]
        )
        if not existing_profile:
            # Create profile first (use user ID suffix to avoid username conflicts)
            email_name = user.get("email", "").split("@")[0] if user.get("email") else "user"
            unique_username = f"{email_name}_{user['id'][:8]}"
            await conn.execute("""
                INSERT INTO profiles (id, username, full_name, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """, user["id"], unique_username, email_name)

        # Check if username is taken (if changing)
        if data.username:
            existing = await conn.fetchrow("""
                SELECT id FROM profiles WHERE username = $1 AND id != $2
            """, data.username, user["id"])
            if existing:
                raise HTTPException(status_code=400, detail="Username already taken")

        # Build update query dynamically
        updates = []
        values = []
        param_num = 1

        if data.full_name is not None:
            updates.append(f"full_name = ${param_num}")
            values.append(data.full_name)
            param_num += 1
        if data.username is not None:
            updates.append(f"username = ${param_num}")
            values.append(data.username)
            param_num += 1
        if data.bio is not None:
            updates.append(f"bio = ${param_num}")
            values.append(data.bio)
            param_num += 1
        if data.avatar_url is not None:
            updates.append(f"avatar_url = ${param_num}")
            values.append(data.avatar_url)
            param_num += 1
        if data.law_school is not None:
            updates.append(f"law_school = ${param_num}")
            values.append(data.law_school)
            param_num += 1
        if data.graduation_year is not None:
            updates.append(f"graduation_year = ${param_num}")
            values.append(data.graduation_year)
            param_num += 1
        if data.is_public is not None:
            updates.append(f"is_public = ${param_num}")
            values.append(data.is_public)
            param_num += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        values.append(user["id"])

        query = f"""
            UPDATE profiles SET {', '.join(updates)}
            WHERE id = ${param_num}
            RETURNING id, username, full_name, avatar_url, bio, reputation,
                      law_school, graduation_year, is_public, created_at, updated_at
        """

        profile = await conn.fetchrow(query, *values)

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "id": profile["id"],
        "username": profile["username"],
        "full_name": profile["full_name"],
        "avatar_url": profile["avatar_url"],
        "bio": profile["bio"],
        "reputation": profile["reputation"] or 0,
        "law_school": profile["law_school"],
        "graduation_year": profile["graduation_year"],
        "is_public": profile["is_public"] or False,
        "created_at": profile["created_at"].isoformat() if profile["created_at"] else None,
        "updated_at": profile["updated_at"].isoformat() if profile["updated_at"] else None
    }


@app.get("/api/v1/profile/comments")
async def get_own_comments(user: dict = Depends(require_auth)):
    """Get all comments by the current user with case info"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.id, c.case_id, c.content, c.is_edited, c.created_at, c.updated_at,
                   cs.title as case_title, cs.reporter_cite
            FROM comments c
            JOIN cases cs ON c.case_id = cs.id
            WHERE c.user_id = $1
            ORDER BY c.created_at DESC
        """, user["id"])

    return {
        "comments": [
            {
                "id": row["id"],
                "case_id": row["case_id"],
                "case_title": row["case_title"],
                "case_cite": row["reporter_cite"],
                "content": row["content"],
                "is_edited": row["is_edited"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
            }
            for row in rows
        ],
        "count": len(rows)
    }


# ============================================================================
# BYOK (Bring Your Own Key) Endpoints
# ============================================================================

@app.get("/api/v1/profile/api-key")
async def get_api_key_status(user: dict = Depends(require_auth)):
    """Check if user has a stored API key"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT api_key_preview FROM profiles WHERE id = $1",
            user["id"],
        )
    has_key = bool(row and row["api_key_preview"])
    return {
        "has_key": has_key,
        "key_preview": row["api_key_preview"] if has_key else None,
    }


@app.post("/api/v1/profile/api-key")
async def save_api_key(body: ApiKeyRequest, user: dict = Depends(require_auth)):
    """Validate and store an Anthropic API key"""
    key = body.anthropic_api_key.strip()

    if not key.startswith("sk-ant-"):
        raise HTTPException(status_code=400, detail="Invalid key format. Anthropic keys start with sk-ant-")

    # Validate key with a small test call
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
                timeout=15.0,
            )
        if resp.status_code == 401:
            raise HTTPException(status_code=400, detail="Invalid API key. Please check and try again.")
        if resp.status_code == 403:
            raise HTTPException(status_code=400, detail="API key does not have permission. Check your Anthropic account.")
        if resp.status_code not in (200, 429):
            raise HTTPException(status_code=400, detail=f"Key validation failed (status {resp.status_code})")
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Could not validate key - Anthropic API timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Key validation error: {str(e)}")

    # Encrypt and store
    preview = make_key_preview(key)
    encrypted = encrypt_api_key(key)

    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE profiles SET encrypted_api_key = $1, api_key_preview = $2 WHERE id = $3",
            encrypted, preview, user["id"],
        )

    return {"valid": True, "key_preview": preview}


@app.delete("/api/v1/profile/api-key")
async def remove_api_key(user: dict = Depends(require_auth)):
    """Remove stored API key"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE profiles SET encrypted_api_key = NULL, api_key_preview = NULL WHERE id = $1",
            user["id"],
        )
    return {"status": "removed"}


@app.get("/api/v1/users/{username}")
async def get_public_profile(username: str):
    """Get a public user profile by username"""
    async with db_pool.acquire() as conn:
        profile = await conn.fetchrow("""
            SELECT id, username, full_name, avatar_url, bio, reputation,
                   law_school, graduation_year, is_public, created_at
            FROM profiles WHERE username = $1
        """, username)

        if not profile:
            raise HTTPException(status_code=404, detail="User not found")

        if not profile["is_public"]:
            # Return limited info for private profiles
            return {
                "username": profile["username"],
                "avatar_url": profile["avatar_url"],
                "is_public": False,
                "message": "This profile is private"
            }

    return {
        "id": profile["id"],
        "username": profile["username"],
        "full_name": profile["full_name"],
        "avatar_url": profile["avatar_url"],
        "bio": profile["bio"],
        "reputation": profile["reputation"] or 0,
        "law_school": profile["law_school"],
        "graduation_year": profile["graduation_year"],
        "is_public": True,
        "created_at": profile["created_at"].isoformat() if profile["created_at"] else None
    }


@app.get("/api/v1/users/{username}/comments")
async def get_user_comments(username: str):
    """Get public comments by a user"""
    async with db_pool.acquire() as conn:
        # Check if profile exists and is public
        profile = await conn.fetchrow("""
            SELECT id, is_public FROM profiles WHERE username = $1
        """, username)

        if not profile:
            raise HTTPException(status_code=404, detail="User not found")

        if not profile["is_public"]:
            raise HTTPException(status_code=403, detail="This profile is private")

        rows = await conn.fetch("""
            SELECT c.id, c.case_id, c.content, c.is_edited, c.created_at,
                   cs.title as case_title, cs.reporter_cite
            FROM comments c
            JOIN cases cs ON c.case_id = cs.id
            WHERE c.user_id = $1
            ORDER BY c.created_at DESC
            LIMIT 50
        """, profile["id"])

    return {
        "comments": [
            {
                "id": row["id"],
                "case_id": row["case_id"],
                "case_title": row["case_title"],
                "case_cite": row["reporter_cite"],
                "content": row["content"][:200] + ("..." if len(row["content"]) > 200 else ""),
                "is_edited": row["is_edited"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            }
            for row in rows
        ],
        "count": len(rows)
    }


# ============================================================================
# Comments
# ============================================================================

@app.get("/api/v1/cases/{case_id}/comments")
async def get_comments(case_id: str, user: Optional[dict] = Depends(get_current_user)):
    """Get all comments for a case with user info and vote counts"""
    user_id = user["id"] if user else None
    async with db_pool.acquire() as conn:
        # Verify case exists
        case = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Get comments with user profile info and vote counts (graceful fallback)
        try:
            if user_id:
                rows = await conn.fetch("""
                    SELECT c.id, c.case_id, c.user_id, c.content, c.is_edited,
                           c.created_at, c.updated_at, c.author_name,
                           p.username, p.full_name, p.avatar_url,
                           COALESCE(vc.vote_count, 0) as vote_count,
                           uv.vote_type as user_vote
                    FROM comments c
                    LEFT JOIN profiles p ON c.user_id = p.id
                    LEFT JOIN (
                        SELECT comment_id, SUM(vote_type) as vote_count
                        FROM public.comment_votes GROUP BY comment_id
                    ) vc ON c.id = vc.comment_id
                    LEFT JOIN public.comment_votes uv ON c.id = uv.comment_id AND uv.user_id = $2
                    WHERE c.case_id = $1
                    ORDER BY COALESCE(vc.vote_count, 0) DESC, c.created_at ASC
                """, case_id, user_id)
            else:
                rows = await conn.fetch("""
                    SELECT c.id, c.case_id, c.user_id, c.content, c.is_edited,
                           c.created_at, c.updated_at, c.author_name,
                           p.username, p.full_name, p.avatar_url,
                           COALESCE(vc.vote_count, 0) as vote_count,
                           NULL::integer as user_vote
                    FROM comments c
                    LEFT JOIN profiles p ON c.user_id = p.id
                    LEFT JOIN (
                        SELECT comment_id, SUM(vote_type) as vote_count
                        FROM public.comment_votes GROUP BY comment_id
                    ) vc ON c.id = vc.comment_id
                    WHERE c.case_id = $1
                    ORDER BY COALESCE(vc.vote_count, 0) DESC, c.created_at ASC
                """, case_id)
            has_votes = True
        except Exception:
            # Fallback if comment_votes table doesn't exist
            rows = await conn.fetch("""
                SELECT c.id, c.case_id, c.user_id, c.content, c.is_edited,
                       c.created_at, c.updated_at, c.author_name,
                       p.username, p.full_name, p.avatar_url
                FROM comments c
                LEFT JOIN profiles p ON c.user_id = p.id
                WHERE c.case_id = $1
                ORDER BY c.created_at ASC
            """, case_id)
            has_votes = False

    return {
        "comments": [
            {
                "id": row["id"],
                "case_id": row["case_id"],
                "user_id": row["user_id"],
                "content": row["content"],
                "is_edited": row["is_edited"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "vote_count": int(row["vote_count"]) if has_votes else 0,
                "user_vote": (int(row["user_vote"]) if row["user_vote"] is not None else None) if has_votes else None,
                "user": {
                    "username": row["author_name"] or row["username"],
                    "display_name": row["author_name"] or row["full_name"],
                    "avatar_url": row["avatar_url"],
                    "profile_username": row["username"]
                }
            }
            for row in rows
        ],
        "count": len(rows)
    }


@app.post("/api/v1/cases/{case_id}/comments")
async def create_comment(case_id: str, data: CommentCreate, user: dict = Depends(require_auth)):
    """Create a new comment on a case"""
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    # Determine author name: profile name > email username
    email_name = user.get("email", "").split("@")[0] if user.get("email") else None

    async with db_pool.acquire() as conn:
        # Verify case exists
        case = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Get user profile for author name
        profile = await conn.fetchrow("""
            SELECT username, full_name, avatar_url FROM profiles WHERE id = $1
        """, user["id"])

        # Use profile name, then email username as fallback
        author_name = None
        if profile:
            author_name = profile["full_name"] or profile["username"]
        if not author_name:
            author_name = email_name

        # Create comment with author_name stored
        row = await conn.fetchrow("""
            INSERT INTO comments (case_id, user_id, content, author_name)
            VALUES ($1, $2, $3, $4)
            RETURNING id, case_id, user_id, content, is_edited, created_at, updated_at, author_name
        """, case_id, user["id"], data.content.strip(), author_name)

    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "user_id": row["user_id"],
        "content": row["content"],
        "is_edited": row["is_edited"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "vote_count": 0,
        "user_vote": None,
        "user": {
            "username": row["author_name"],
            "display_name": row["author_name"],
            "avatar_url": profile["avatar_url"] if profile else None
        }
    }


@app.put("/api/v1/comments/{comment_id}")
async def update_comment(comment_id: int, data: CommentUpdate, user: dict = Depends(require_auth)):
    """Update own comment"""
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    async with db_pool.acquire() as conn:
        # Verify comment exists and belongs to user
        comment = await conn.fetchrow("""
            SELECT id, user_id FROM comments WHERE id = $1
        """, comment_id)

        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        if comment["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only edit your own comments")

        # Update comment
        row = await conn.fetchrow("""
            UPDATE comments
            SET content = $1, is_edited = TRUE, updated_at = NOW()
            WHERE id = $2
            RETURNING id, case_id, user_id, content, is_edited, created_at, updated_at
        """, data.content.strip(), comment_id)

        # Get user profile for response
        profile = await conn.fetchrow("""
            SELECT username, full_name, avatar_url FROM profiles WHERE id = $1
        """, user["id"])

        # Get current vote count for this comment (graceful if table missing)
        vote_count = 0
        uv = None
        try:
            vote_count = await conn.fetchval(
                "SELECT COALESCE(SUM(vote_type), 0) FROM public.comment_votes WHERE comment_id = $1",
                comment_id
            )
            uv = await conn.fetchrow(
                "SELECT vote_type FROM public.comment_votes WHERE comment_id = $1 AND user_id = $2",
                comment_id, user["id"]
            )
        except Exception:
            pass

    # Use email as fallback if no profile exists
    email_name = user.get("email", "").split("@")[0] if user.get("email") else None

    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "user_id": row["user_id"],
        "content": row["content"],
        "is_edited": row["is_edited"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "vote_count": int(vote_count),
        "user_vote": uv["vote_type"] if uv else None,
        "user": {
            "username": profile["username"] if profile else email_name,
            "display_name": profile["full_name"] if profile else email_name,
            "avatar_url": profile["avatar_url"] if profile else None
        }
    }


@app.delete("/api/v1/comments/{comment_id}")
async def delete_comment(comment_id: int, user: dict = Depends(require_auth)):
    """Delete own comment, undoing any reputation effects from votes"""
    async with db_pool.acquire() as conn:
        # Verify comment exists and belongs to user
        comment = await conn.fetchrow("""
            SELECT id, user_id FROM comments WHERE id = $1
        """, comment_id)

        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        if comment["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only delete your own comments")

        # Undo reputation from votes on this comment (graceful if table missing)
        try:
            vote_sum = await conn.fetchval(
                "SELECT COALESCE(SUM(vote_type), 0) FROM public.comment_votes WHERE comment_id = $1",
                comment_id
            )
            if vote_sum != 0:
                await conn.execute(
                    "UPDATE profiles SET reputation = COALESCE(reputation, 0) - $1 WHERE id = $2",
                    vote_sum, comment["user_id"]
                )
        except Exception:
            pass

        # Delete comment
        await conn.execute("DELETE FROM comments WHERE id = $1", comment_id)

    return {"status": "deleted"}


@app.post("/api/v1/comments/{comment_id}/vote")
async def vote_comment(comment_id: int, data: CommentVote, user: dict = Depends(require_auth)):
    """Vote on a comment. Send 1 (upvote), -1 (downvote), or 0 to remove vote."""
    if data.vote_type not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="vote_type must be -1, 0, or 1")

    try:
        async with db_pool.acquire() as conn:
            # Verify comment exists
            comment = await conn.fetchrow("SELECT id, user_id FROM comments WHERE id = $1", comment_id)
            if not comment:
                raise HTTPException(status_code=404, detail="Comment not found")

            # Block self-voting
            if comment["user_id"] == str(user["id"]):
                raise HTTPException(status_code=400, detail="You cannot vote on your own comment")

            # Get existing vote
            existing = await conn.fetchrow(
                "SELECT vote_type FROM public.comment_votes WHERE comment_id = $1 AND user_id = $2",
                comment_id, str(user["id"])
            )
            old_vote = existing["vote_type"] if existing else 0

            if data.vote_type == 0:
                # Remove vote
                if existing:
                    await conn.execute(
                        "DELETE FROM public.comment_votes WHERE comment_id = $1 AND user_id = $2",
                        comment_id, str(user["id"])
                    )
            else:
                # Upsert vote
                await conn.execute("""
                    INSERT INTO public.comment_votes (comment_id, user_id, vote_type)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (comment_id, user_id) DO UPDATE SET vote_type = EXCLUDED.vote_type
                """, comment_id, str(user["id"]), int(data.vote_type))

            # Update reputation on comment author: delta = new_vote - old_vote
            new_vote = data.vote_type
            delta = new_vote - old_vote
            if delta != 0:
                await conn.execute(
                    "UPDATE profiles SET reputation = COALESCE(reputation, 0) + $1 WHERE id = $2",
                    int(delta), comment["user_id"]
                )

            # Get updated vote count
            vote_count = await conn.fetchval(
                "SELECT COALESCE(SUM(vote_type), 0) FROM public.comment_votes WHERE comment_id = $1",
                comment_id
            )

            # Get user's current vote
            uv = await conn.fetchrow(
                "SELECT vote_type FROM public.comment_votes WHERE comment_id = $1 AND user_id = $2",
                comment_id, str(user["id"])
            )

        return {
            "comment_id": comment_id,
            "vote_count": int(vote_count),
            "user_vote": uv["vote_type"] if uv else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in vote_comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Outlines (community outline sharing)
# ============================================================================

@app.get("/api/v1/outlines")
async def list_outlines(subject: Optional[str] = None, limit: int = 50, offset: int = 0):
    """Browse public outlines, optionally filtered by subject"""
    async with db_pool.acquire() as conn:
        if subject:
            rows = await conn.fetch("""
                SELECT o.id, o.user_id, o.title, o.subject, o.professor, o.law_school,
                       o.semester, o.description, o.filename, o.file_url, o.file_size,
                       o.file_type, o.download_count, o.created_at,
                       p.username, p.full_name
                FROM outlines o
                LEFT JOIN profiles p ON o.user_id = p.id
                WHERE o.is_public = TRUE AND o.subject = $1
                ORDER BY o.created_at DESC
                LIMIT $2 OFFSET $3
            """, subject, limit, offset)
        else:
            rows = await conn.fetch("""
                SELECT o.id, o.user_id, o.title, o.subject, o.professor, o.law_school,
                       o.semester, o.description, o.filename, o.file_url, o.file_size,
                       o.file_type, o.download_count, o.created_at,
                       p.username, p.full_name
                FROM outlines o
                LEFT JOIN profiles p ON o.user_id = p.id
                WHERE o.is_public = TRUE
                ORDER BY o.created_at DESC
                LIMIT $1 OFFSET $2
            """, limit, offset)

    return {
        "outlines": [
            {
                "id": row["id"],
                "title": row["title"],
                "subject": row["subject"],
                "professor": row["professor"],
                "law_school": row["law_school"],
                "semester": row["semester"],
                "description": row["description"],
                "filename": row["filename"],
                "file_url": row["file_url"],
                "file_size": row["file_size"],
                "file_type": row["file_type"],
                "download_count": row["download_count"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "username": row["username"],
                "full_name": row["full_name"],
            }
            for row in rows
        ]
    }


@app.get("/api/v1/outlines/subjects")
async def list_outline_subjects():
    """List subjects with outline counts"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT subject, COUNT(*) as count
            FROM outlines
            WHERE is_public = TRUE
            GROUP BY subject
            ORDER BY count DESC
        """)

    return {
        "subjects": [
            {"subject": row["subject"], "count": row["count"]}
            for row in rows
        ]
    }


@app.get("/api/v1/outlines/mine")
async def list_my_outlines(user: dict = Depends(require_auth)):
    """List current user's outlines"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, subject, professor, law_school, semester, description,
                   filename, file_url, file_size, file_type, is_public, download_count, created_at
            FROM outlines
            WHERE user_id = $1
            ORDER BY created_at DESC
        """, user["id"])

    return {
        "outlines": [
            {
                "id": row["id"],
                "title": row["title"],
                "subject": row["subject"],
                "professor": row["professor"],
                "law_school": row["law_school"],
                "semester": row["semester"],
                "description": row["description"],
                "filename": row["filename"],
                "file_url": row["file_url"],
                "file_size": row["file_size"],
                "file_type": row["file_type"],
                "is_public": row["is_public"],
                "download_count": row["download_count"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
    }


@app.post("/api/v1/outlines")
async def create_outline(outline: OutlineCreate, user: dict = Depends(require_auth)):
    """Create a new outline (metadata only; file already uploaded to Supabase Storage)"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO outlines (user_id, title, subject, professor, law_school, semester,
                                  description, filename, file_url, file_size, file_type, is_public)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id, title, subject, professor, law_school, semester, description,
                      filename, file_url, file_size, file_type, is_public, download_count, created_at
        """, user["id"], outline.title, outline.subject, outline.professor, outline.law_school,
            outline.semester, outline.description, outline.filename, outline.file_url,
            outline.file_size, outline.file_type, outline.is_public)

    return {
        "id": row["id"],
        "title": row["title"],
        "subject": row["subject"],
        "professor": row["professor"],
        "law_school": row["law_school"],
        "semester": row["semester"],
        "description": row["description"],
        "filename": row["filename"],
        "file_url": row["file_url"],
        "file_size": row["file_size"],
        "file_type": row["file_type"],
        "is_public": row["is_public"],
        "download_count": row["download_count"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.get("/api/v1/outlines/{outline_id}")
async def get_outline(outline_id: int, user: Optional[dict] = Depends(get_current_user)):
    """Get a single outline and increment download count"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT o.id, o.user_id, o.title, o.subject, o.professor, o.law_school,
                   o.semester, o.description, o.filename, o.file_url, o.file_size,
                   o.file_type, o.is_public, o.download_count, o.created_at,
                   p.username, p.full_name
            FROM outlines o
            LEFT JOIN profiles p ON o.user_id = p.id
            WHERE o.id = $1
        """, outline_id)

        if not row:
            raise HTTPException(status_code=404, detail="Outline not found")

        # Private outlines require ownership
        if not row["is_public"]:
            if not user or user["id"] != row["user_id"]:
                raise HTTPException(status_code=404, detail="Outline not found")

        # Increment download count
        await conn.execute(
            "UPDATE outlines SET download_count = download_count + 1 WHERE id = $1",
            outline_id
        )

    return {
        "id": row["id"],
        "title": row["title"],
        "subject": row["subject"],
        "professor": row["professor"],
        "law_school": row["law_school"],
        "semester": row["semester"],
        "description": row["description"],
        "filename": row["filename"],
        "file_url": row["file_url"],
        "file_size": row["file_size"],
        "file_type": row["file_type"],
        "download_count": row["download_count"] + 1,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "username": row["username"],
        "full_name": row["full_name"],
    }


@app.delete("/api/v1/outlines/{outline_id}")
async def delete_outline(outline_id: int, user: dict = Depends(require_auth)):
    """Delete own outline"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id, file_url FROM outlines WHERE id = $1", outline_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Outline not found")

        if row["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only delete your own outlines")

        await conn.execute("DELETE FROM outlines WHERE id = $1", outline_id)

    return {"status": "deleted", "file_url": row["file_url"]}


# ============================================================================
# Study Assistant (AI chat with uploaded notes)
# ============================================================================

class ChatMessage(BaseModel):
    content: str
    conversation_id: Optional[int] = None
    note_ids: Optional[List[int]] = None

class CaseAskMessage(BaseModel):
    content: str
    conversation_id: Optional[int] = None

class SessionStart(BaseModel):
    mindmap_id: int
    branch_node_id: Optional[str] = None

class SessionRespond(BaseModel):
    answer: str
    response_time_ms: int = 0

# --- Notes CRUD ---

@app.post("/api/v1/study/notes/upload")
async def upload_study_note(
    file: UploadFile = File(...),
    title: str = Form(...),
    tags: Optional[str] = Form(None),
    user: dict = Depends(require_auth),
):
    """Upload a study note file, extract text, store in DB"""
    # Validate file type
    filename = file.filename or "untitled"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "docx", "txt"):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported")

    content = await file.read()
    file_size = len(content)

    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size limit is 10MB")

    # Extract text
    if ext == "pdf":
        extracted_text = extract_text_from_pdf(content)
    elif ext == "docx":
        extracted_text = extract_text_from_docx(content)
    else:
        extracted_text = content.decode("utf-8", errors="replace")

    if not extracted_text or len(extracted_text) < 10:
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    char_count = len(extracted_text)

    # Parse comma-separated tags into list
    tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else None

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO study_notes (user_id, title, tags, filename, file_size, file_type, extracted_text, char_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, title, tags, filename, file_size, file_type, char_count, created_at
        """, user["id"], title, tag_list, filename, file_size, ext, extracted_text, char_count)

    return {
        "id": row["id"],
        "title": row["title"],
        "tags": list(row["tags"]) if row["tags"] else None,
        "filename": row["filename"],
        "file_size": row["file_size"],
        "file_type": row["file_type"],
        "char_count": row["char_count"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.get("/api/v1/study/notes")
async def list_study_notes(user: dict = Depends(require_auth)):
    """List user's study notes"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, title, tags, filename, file_size, file_type, char_count, created_at
            FROM study_notes
            WHERE user_id = $1
            ORDER BY created_at DESC
        """, user["id"])

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "tags": list(row["tags"]) if row["tags"] else None,
            "filename": row["filename"],
            "file_size": row["file_size"],
            "file_type": row["file_type"],
            "char_count": row["char_count"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@app.delete("/api/v1/study/notes/{note_id}")
async def delete_study_note(note_id: int, user: dict = Depends(require_auth)):
    """Delete a study note"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM study_notes WHERE id = $1", note_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
        if row["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only delete your own notes")

        await conn.execute("DELETE FROM study_notes WHERE id = $1", note_id)

    return {"status": "deleted"}


@app.get("/api/v1/study/tags")
async def list_study_tags(user: dict = Depends(require_auth)):
    """Return user's unique tags with note counts (for autocomplete)"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT unnest(tags) AS tag, COUNT(*) AS count
            FROM study_notes
            WHERE user_id = $1 AND tags IS NOT NULL
            GROUP BY tag
            ORDER BY count DESC, tag
        """, user["id"])

    return [{"tag": row["tag"], "count": row["count"]} for row in rows]


class TagsUpdate(BaseModel):
    tags: List[str]


@app.patch("/api/v1/study/notes/{note_id}/tags")
async def update_note_tags(note_id: int, body: TagsUpdate, user: dict = Depends(require_auth)):
    """Update tags on an existing note"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM study_notes WHERE id = $1", note_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Note not found")
        if row["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only update your own notes")

        tag_list = [t.strip() for t in body.tags if t.strip()] or None
        await conn.execute(
            "UPDATE study_notes SET tags = $1 WHERE id = $2",
            tag_list, note_id
        )

    return {"status": "updated", "tags": tag_list}


# --- Conversations CRUD ---

@app.get("/api/v1/study/conversations")
async def list_conversations(user: dict = Depends(require_auth)):
    """List user's conversations with message counts"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.id, c.title, c.note_ids, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE c.user_id = $1
            GROUP BY c.id
            ORDER BY c.updated_at DESC
        """, user["id"])

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "note_ids": row["note_ids"] or [],
            "message_count": row["message_count"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        for row in rows
    ]


@app.get("/api/v1/study/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, user: dict = Depends(require_auth)):
    """Get a conversation with all messages"""
    async with db_pool.acquire() as conn:
        convo = await conn.fetchrow(
            "SELECT id, user_id, title, note_ids, created_at, updated_at FROM conversations WHERE id = $1",
            conversation_id,
        )
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if convo["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your conversation")

        msgs = await conn.fetch("""
            SELECT id, role, content, model, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
        """, conversation_id)

    return {
        "id": convo["id"],
        "title": convo["title"],
        "note_ids": convo["note_ids"] or [],
        "created_at": convo["created_at"].isoformat() if convo["created_at"] else None,
        "updated_at": convo["updated_at"].isoformat() if convo["updated_at"] else None,
        "messages": [
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "model": m["model"],
                "created_at": m["created_at"].isoformat() if m["created_at"] else None,
            }
            for m in msgs
        ],
    }


@app.delete("/api/v1/study/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user: dict = Depends(require_auth)):
    """Delete a conversation and its messages"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id FROM conversations WHERE id = $1", conversation_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if row["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not your conversation")

        await conn.execute("DELETE FROM conversations WHERE id = $1", conversation_id)

    return {"status": "deleted"}


# --- Usage endpoint ---

@app.get("/api/v1/study/usage")
async def get_study_usage(user: dict = Depends(require_auth)):
    """Get user's tier and daily usage info"""
    # Check BYOK status
    has_byok = await get_user_api_key(user["id"]) is not None

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tier, messages_today, last_message_date, daily_limit, model_override FROM user_tiers WHERE user_id = $1",
            user["id"],
        )

    if not row:
        if has_byok:
            return {
                "tier": "free",
                "messages_today": 0,
                "daily_limit": None,
                "messages_remaining": None,
                "model": "claude-sonnet-4-6",
                "is_byok": True,
            }
        return {
            "tier": "free",
            "messages_today": 0,
            "daily_limit": 15,
            "messages_remaining": 15,
            "model": "claude-haiku-4-5-20251001",
            "is_byok": False,
        }

    tier = row["tier"]
    messages_today = row["messages_today"]
    if row["last_message_date"] != date.today():
        messages_today = 0

    # BYOK users get unlimited
    if has_byok:
        daily_limit = None
    else:
        custom_limit = row["daily_limit"]
        if custom_limit is not None:
            daily_limit = custom_limit
        elif tier == "pro":
            daily_limit = None
        else:
            daily_limit = 15

    messages_remaining = None if daily_limit is None else max(0, daily_limit - messages_today)

    if has_byok:
        default_model = "claude-sonnet-4-6"
    elif tier == "pro":
        default_model = "claude-sonnet-4-6"
    else:
        default_model = "claude-haiku-4-5-20251001"
    model = row["model_override"] or default_model

    return {
        "tier": tier,
        "messages_today": messages_today,
        "daily_limit": daily_limit,
        "messages_remaining": messages_remaining,
        "model": model,
        "is_byok": has_byok,
    }


# --- Chat SSE endpoint ---

@app.post("/api/v1/study/chat")
async def study_chat(msg: ChatMessage, user: dict = Depends(require_auth)):
    """Stream AI study assistant response via SSE"""
    user_id = user["id"]

    # Check for BYOK
    user_api_key = await get_user_api_key(user_id)
    is_byok = user_api_key is not None
    chat_api_key = user_api_key or ANTHROPIC_API_KEY
    if not chat_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Check community pool for non-BYOK users
    if not is_byok:
        if not await check_pool_available(user_id):
            raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)

    async with db_pool.acquire() as conn:
        # Get or create user tier
        tier_row = await conn.fetchrow(
            "SELECT tier, messages_today, last_message_date, daily_limit, model_override FROM user_tiers WHERE user_id = $1",
            user_id,
        )

        if not tier_row:
            await conn.execute(
                "INSERT INTO user_tiers (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                user_id,
            )
            tier = "free"
            messages_today = 0
            custom_limit = None
            model_override = None
        else:
            tier = tier_row["tier"]
            messages_today = tier_row["messages_today"]
            if tier_row["last_message_date"] != date.today():
                messages_today = 0
            custom_limit = tier_row["daily_limit"]
            model_override = tier_row["model_override"]

        # BYOK users get unlimited access and Sonnet
        if is_byok:
            effective_limit = None
        elif custom_limit is not None:
            effective_limit = custom_limit
        elif tier == "pro":
            effective_limit = None  # unlimited
        else:
            effective_limit = 15

        # Check daily limit (skipped for BYOK)
        if effective_limit is not None and messages_today >= effective_limit:
            raise HTTPException(
                status_code=429,
                detail="Daily message limit reached. Upgrade to Pro for unlimited messages.",
            )

        # Select model — BYOK users get Sonnet
        if is_byok:
            default_model = "claude-sonnet-4-6"
        elif tier == "pro":
            default_model = "claude-sonnet-4-6"
        else:
            default_model = "claude-haiku-4-5-20251001"
        model = model_override or default_model

        # Create or get conversation
        conversation_id = msg.conversation_id
        if not conversation_id:
            title = msg.content[:80].strip()
            if len(msg.content) > 80:
                title += "..."
            row = await conn.fetchrow("""
                INSERT INTO conversations (user_id, title, note_ids)
                VALUES ($1, $2, $3)
                RETURNING id
            """, user_id, title, msg.note_ids or [])
            conversation_id = row["id"]
        else:
            # Verify ownership
            convo = await conn.fetchrow(
                "SELECT user_id FROM conversations WHERE id = $1", conversation_id
            )
            if not convo or convo["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Not your conversation")

        # Save user message
        await conn.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES ($1, 'user', $2)
        """, conversation_id, msg.content)

        # Update conversation timestamp
        await conn.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
            conversation_id,
        )

        # Build context: get notes text
        notes_context = ""
        note_ids = msg.note_ids
        if not note_ids and msg.conversation_id:
            convo_row = await conn.fetchrow(
                "SELECT note_ids FROM conversations WHERE id = $1", conversation_id
            )
            note_ids = convo_row["note_ids"] if convo_row and convo_row["note_ids"] else []

        if note_ids:
            notes = await conn.fetch("""
                SELECT title, extracted_text FROM study_notes
                WHERE id = ANY($1) AND user_id = $2
            """, note_ids, user_id)
            for note in notes:
                text = note["extracted_text"] or ""
                if len(text) > 30000:
                    text = text[:30000] + "\n...[truncated]"
                notes_context += f"\n\n--- Student's Note: {note['title']} ---\n{text}"

            # Cap total notes context
            if len(notes_context) > 120000:
                notes_context = notes_context[:120000] + "\n...[notes truncated]"

        # FTS search for relevant case briefs from ai_summaries
        briefs_context = ""
        try:
            brief_rows = await conn.fetch("""
                SELECT s.summary, c.title as case_title
                FROM ai_summaries s
                JOIN cases c ON s.case_id = c.id
                WHERE to_tsvector('english', s.summary) @@ plainto_tsquery('english', $1)
                LIMIT 5
            """, msg.content)
            for br in brief_rows:
                briefs_context += f"\n\n--- Case Brief: {br['case_title']} ---\n{br['summary'][:3000]}"
        except Exception as e:
            print(f"FTS brief lookup failed: {e}")

        # Get conversation history (last 20 messages)
        history = await conn.fetch("""
            SELECT role, content FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at DESC
            LIMIT 20
        """, conversation_id)
        history = list(reversed(history))

    # Build system prompt
    system_prompt = """You are a law school study assistant. You help students understand legal concepts, prepare for exams, and analyze cases.

Guidelines:
- Reference the student's uploaded notes when relevant, citing specific passages
- Cite cases accurately using proper legal citation format
- Use the Socratic method when appropriate — ask guiding questions to deepen understanding
- Structure responses clearly with headers and bullet points when helpful
- Be concise but thorough — law students are busy
- If you're unsure about something, say so rather than guessing"""

    if notes_context:
        system_prompt += f"\n\nThe student has shared these study notes for reference:{notes_context}"
    if briefs_context:
        system_prompt += f"\n\nRelevant case briefs from our database:{briefs_context}"

    # Build messages for API (skip last entry which is the user msg we just added)
    api_messages = []
    for h in history:
        api_messages.append({"role": h["role"], "content": h["content"]})

    async def stream_response():
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"

        full_response = ""
        input_tokens = 0
        output_tokens = 0

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": chat_api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 4096,
                        "system": system_prompt,
                        "messages": api_messages,
                        "stream": True,
                    },
                    timeout=120.0,
                ) as response:
                    if response.status_code != 200:
                        error_body = ""
                        async for chunk in response.aiter_text():
                            error_body += chunk
                        print(f"Study chat API error {response.status_code}: {error_body[:500]}")
                        yield f"data: {json.dumps({'type': 'error', 'error': f'API error {response.status_code}'})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = event.get("type", "")

                        if event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                full_response += text
                                yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

                        elif event_type == "message_start":
                            usage = event.get("message", {}).get("usage", {})
                            input_tokens = usage.get("input_tokens", 0)

                        elif event_type == "message_delta":
                            usage = event.get("usage", {})
                            output_tokens = usage.get("output_tokens", 0)

        except Exception as e:
            print(f"Study chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return

        # Calculate cost
        if "haiku" in model:
            cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
            usage_type = "study_chat_haiku"
        else:
            cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
            usage_type = "study_chat_sonnet"

        # Save assistant message, update usage
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO messages (conversation_id, role, content, model, input_tokens, output_tokens, cost)
                    VALUES ($1, 'assistant', $2, $3, $4, $5, $6)
                """, conversation_id, full_response, model, input_tokens, output_tokens, cost)

                await conn.execute("""
                    INSERT INTO user_tiers (user_id, messages_today, last_message_date, updated_at)
                    VALUES ($1, 1, CURRENT_DATE, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        messages_today = CASE
                            WHEN user_tiers.last_message_date = CURRENT_DATE
                            THEN user_tiers.messages_today + 1
                            ELSE 1
                        END,
                        last_message_date = CURRENT_DATE,
                        updated_at = NOW()
                """, user_id)

                await conn.execute(
                    "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
                    conversation_id,
                )

            await log_api_usage(usage_type, input_tokens, output_tokens, cost, source="byok" if is_byok else "site")
        except Exception as e:
            print(f"Failed to save chat result: {e}")

        # Final done event
        remaining = None
        if effective_limit is not None:
            remaining = max(0, effective_limit - (messages_today + 1))
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cost': round(cost, 6)}, 'tier': tier, 'messages_remaining': remaining, 'is_byok': is_byok})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Case Ask AI
# ============================================================================

@app.post("/api/v1/cases/{case_id}/ask")
async def case_ask_ai(case_id: str, msg: CaseAskMessage, user: dict = Depends(require_auth)):
    """Stream AI response about a specific case via SSE"""
    user_id = user["id"]

    # Check for BYOK
    user_api_key = await get_user_api_key(user_id)
    is_byok = user_api_key is not None
    chat_api_key = user_api_key or ANTHROPIC_API_KEY
    if not chat_api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Check community pool for non-BYOK users
    if not is_byok:
        if not await check_pool_available(user_id):
            raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)

    async with db_pool.acquire() as conn:
        # Verify case exists and fetch data
        case_row = await conn.fetchrow(
            "SELECT id, title, content, court_id, decision_date FROM cases WHERE id = $1",
            case_id,
        )
        if not case_row:
            raise HTTPException(status_code=404, detail="Case not found")

        # Fetch cached AI brief if available
        brief_row = await conn.fetchrow(
            "SELECT summary FROM ai_summaries WHERE case_id = $1", case_id
        )

        # Fetch citation network: cases this case cites and cases citing this case
        cited_cases = await conn.fetch("""
            SELECT c.id, c.title, c.reporter_cite, c.decision_date
            FROM citations cit
            JOIN cases c ON cit.target_case_id = c.id
            WHERE cit.source_case_id = $1
            LIMIT 10
        """, case_id)

        citing_cases = await conn.fetch("""
            SELECT c.id, c.title, c.reporter_cite, c.decision_date
            FROM citations cit
            JOIN cases c ON cit.source_case_id = c.id
            WHERE cit.target_case_id = $1
            LIMIT 10
        """, case_id)

        # Fetch cached briefs for all related cases in one query
        related_ids = [r["id"] for r in cited_cases] + [r["id"] for r in citing_cases]
        related_briefs = {}
        if related_ids:
            brief_rows = await conn.fetch(
                "SELECT case_id, summary FROM ai_summaries WHERE case_id = ANY($1)",
                related_ids,
            )
            related_briefs = {r["case_id"]: r["summary"] for r in brief_rows}

        # Get or create user tier (shared with study chat)
        tier_row = await conn.fetchrow(
            "SELECT tier, messages_today, last_message_date, daily_limit, model_override FROM user_tiers WHERE user_id = $1",
            user_id,
        )

        if not tier_row:
            await conn.execute(
                "INSERT INTO user_tiers (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                user_id,
            )
            tier = "free"
            messages_today = 0
            custom_limit = None
            model_override = None
        else:
            tier = tier_row["tier"]
            messages_today = tier_row["messages_today"]
            if tier_row["last_message_date"] != date.today():
                messages_today = 0
            custom_limit = tier_row["daily_limit"]
            model_override = tier_row["model_override"]

        # Compute effective limit — BYOK users get unlimited
        if is_byok:
            effective_limit = None
        elif custom_limit is not None:
            effective_limit = custom_limit
        elif tier == "pro":
            effective_limit = None  # unlimited
        else:
            effective_limit = 15

        # Check daily limit
        if effective_limit is not None and messages_today >= effective_limit:
            raise HTTPException(
                status_code=429,
                detail="Daily message limit reached. Upgrade to Pro for unlimited messages.",
            )

        # Select model — BYOK users get Sonnet
        if is_byok:
            default_model = "claude-sonnet-4-6"
        elif tier == "pro":
            default_model = "claude-sonnet-4-6"
        else:
            default_model = "claude-haiku-4-5-20251001"
        model = model_override or default_model

        # Create or get conversation
        conversation_id = msg.conversation_id
        if not conversation_id:
            title = f"Q about {case_row['title'] or 'case'}: {msg.content[:60].strip()}"
            if len(title) > 100:
                title = title[:97] + "..."
            row = await conn.fetchrow("""
                INSERT INTO conversations (user_id, title, note_ids, case_id)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, user_id, title, [], case_id)
            conversation_id = row["id"]
        else:
            # Verify ownership AND case_id match
            convo = await conn.fetchrow(
                "SELECT user_id, case_id FROM conversations WHERE id = $1", conversation_id
            )
            if not convo or convo["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="Not your conversation")
            if convo["case_id"] != case_id:
                raise HTTPException(status_code=400, detail="Conversation does not belong to this case")

        # Save user message
        await conn.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES ($1, 'user', $2)
        """, conversation_id, msg.content)

        # Update conversation timestamp
        await conn.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
            conversation_id,
        )

        # Get conversation history (last 20 messages)
        history = await conn.fetch("""
            SELECT role, content FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at DESC
            LIMIT 20
        """, conversation_id)
        history = list(reversed(history))

    # Build case context
    case_title = case_row["title"] or "Unknown Case"
    case_court = case_row["court_id"] or "Unknown Court"
    case_date = str(case_row["decision_date"]) if case_row["decision_date"] else "Unknown Date"
    case_text = case_row["content"] or ""
    if len(case_text) > 15000:
        case_text = case_text[:15000] + "\n...[opinion text truncated]"

    ai_brief = brief_row["summary"] if brief_row else ""

    # Build related cases context from citation network
    def format_related_case(row, briefs_dict):
        title = row["title"] or "Unknown"
        cite = row["reporter_cite"] or ""
        yr = str(row["decision_date"].year) if row["decision_date"] else ""
        label = f"{title}, {cite} ({yr})" if cite else f"{title} ({yr})"
        brief = briefs_dict.get(row["id"], "")
        if brief:
            brief = brief[:500].rstrip()
            if len(briefs_dict.get(row["id"], "")) > 500:
                brief += "..."
        return label, brief

    related_context = ""
    if cited_cases or citing_cases:
        parts = []
        if cited_cases:
            lines = ["CASES THIS CASE CITES:"]
            for r in cited_cases:
                label, brief = format_related_case(r, related_briefs)
                lines.append(f"- {label}")
                if brief:
                    lines.append(f"  Brief: {brief}")
            parts.append("\n".join(lines))
        if citing_cases:
            lines = ["CASES CITING THIS CASE:"]
            for r in citing_cases:
                label, brief = format_related_case(r, related_briefs)
                lines.append(f"- {label}")
                if brief:
                    lines.append(f"  Brief: {brief}")
            parts.append("\n".join(lines))
        related_context = "\n\n".join(parts)

    # Build system prompt
    system_prompt = f"""You are a law school tutor helping a student understand the case: {case_title} ({case_court}, {case_date}).

Guidelines:
- Answer questions specifically about this case and its legal significance
- Reference the opinion text and AI brief when relevant
- When relevant, reference related cases from the citation network provided below
- Use the AI briefs of related cases to explain how this case connects to broader legal principles
- ONLY reference the current case and the related cases provided below — do NOT cite any other cases from your own knowledge
- If a student asks about a case not in your context, say you don't have that case in the database yet
- Cite related cases accurately using proper legal citation format
- Use the Socratic method when appropriate — ask guiding questions to deepen understanding
- Structure responses clearly with headers and bullet points when helpful
- Be concise but thorough — law students are busy
- If you're unsure about something, say so rather than guessing"""

    if ai_brief:
        system_prompt += f"\n\nAI-generated case brief:\n{ai_brief}"
    if case_text:
        system_prompt += f"\n\nOpinion text (may be truncated):\n{case_text}"
    if related_context:
        system_prompt += f"\n\nRelated cases in our database (from citation network):\n\n{related_context}"

    # Build messages for API
    api_messages = []
    for h in history:
        api_messages.append({"role": h["role"], "content": h["content"]})

    async def stream_response():
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"

        full_response = ""
        input_tokens = 0
        output_tokens = 0

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": chat_api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 4096,
                        "system": system_prompt,
                        "messages": api_messages,
                        "stream": True,
                    },
                    timeout=120.0,
                ) as response:
                    if response.status_code != 200:
                        error_body = ""
                        async for chunk in response.aiter_text():
                            error_body += chunk
                        print(f"Case ask API error {response.status_code}: {error_body[:500]}")
                        yield f"data: {json.dumps({'type': 'error', 'error': f'API error {response.status_code}'})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = event.get("type", "")

                        if event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                full_response += text
                                yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

                        elif event_type == "message_start":
                            usage = event.get("message", {}).get("usage", {})
                            input_tokens = usage.get("input_tokens", 0)

                        elif event_type == "message_delta":
                            usage = event.get("usage", {})
                            output_tokens = usage.get("output_tokens", 0)

        except Exception as e:
            print(f"Case ask stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return

        # Calculate cost
        if "haiku" in model:
            cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
            usage_type = "case_ask_haiku"
        else:
            cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
            usage_type = "case_ask_sonnet"

        # Save assistant message, update usage
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO messages (conversation_id, role, content, model, input_tokens, output_tokens, cost)
                    VALUES ($1, 'assistant', $2, $3, $4, $5, $6)
                """, conversation_id, full_response, model, input_tokens, output_tokens, cost)

                await conn.execute("""
                    INSERT INTO user_tiers (user_id, messages_today, last_message_date, updated_at)
                    VALUES ($1, 1, CURRENT_DATE, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        messages_today = CASE
                            WHEN user_tiers.last_message_date = CURRENT_DATE
                            THEN user_tiers.messages_today + 1
                            ELSE 1
                        END,
                        last_message_date = CURRENT_DATE,
                        updated_at = NOW()
                """, user_id)

                await conn.execute(
                    "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
                    conversation_id,
                )

            await log_api_usage(usage_type, input_tokens, output_tokens, cost, source="byok" if is_byok else "site")
        except Exception as e:
            print(f"Failed to save case ask result: {e}")

        # Final done event
        remaining = None
        if effective_limit is not None:
            remaining = max(0, effective_limit - (messages_today + 1))
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cost': round(cost, 6)}, 'tier': tier, 'messages_remaining': remaining, 'is_byok': is_byok})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Community Pool
# ============================================================================

@app.get("/api/v1/pool/status")
async def pool_status():
    """Public pool status with recent donors."""
    balance = await get_pool_balance()
    async with db_pool.acquire() as conn:
        config_rows = await conn.fetch("SELECT key, value FROM site_config WHERE key = 'pool_low_threshold'")
        low_threshold = float(config_rows[0]["value"]) if config_rows else 5.0

        donors = await conn.fetch("""
            SELECT from_name, amount, received_at
            FROM donations
            WHERE is_public = true
            ORDER BY received_at DESC
            LIMIT 10
        """)

    return {
        "balance": round(balance, 2),
        "is_healthy": balance > 0,
        "is_low": 0 < balance < low_threshold,
        "recent_donors": [
            {
                "name": d["from_name"],
                "amount": float(d["amount"]),
                "date": d["received_at"].isoformat() if d["received_at"] else None,
            }
            for d in donors
        ],
    }


# ============================================================================
# Admin Panel
# ============================================================================

class PoolAddRequest(BaseModel):
    amount: float
    description: Optional[str] = None


@app.get("/api/v1/admin/pool")
async def admin_pool_info(user: dict = Depends(require_admin)):
    """Get pool balance and recent ledger entries."""
    balance = await get_pool_balance()
    async with db_pool.acquire() as conn:
        config_rows = await conn.fetch("SELECT key, value FROM site_config WHERE key = 'pool_low_threshold'")
        low_threshold = float(config_rows[0]["value"]) if config_rows else 5.0

        entries = await conn.fetch("""
            SELECT id, amount, entry_type, description, reference_id, created_by, created_at
            FROM pool_ledger
            ORDER BY created_at DESC
            LIMIT 50
        """)

    return {
        "balance": round(balance, 2),
        "low_threshold": low_threshold,
        "is_low": 0 < balance < low_threshold,
        "recent_entries": [
            {
                "id": e["id"],
                "amount": float(e["amount"]),
                "entry_type": e["entry_type"],
                "description": e["description"],
                "reference_id": e["reference_id"],
                "created_by": e["created_by"],
                "created_at": e["created_at"].isoformat() if e["created_at"] else None,
            }
            for e in entries
        ],
    }


@app.post("/api/v1/admin/pool/add")
async def admin_pool_add(body: PoolAddRequest, user: dict = Depends(require_admin)):
    """Add funds to the community pool."""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    desc = body.description or "Admin top-up"
    new_balance = await credit_pool(body.amount, "admin_credit", desc, None, user["id"])
    return {"balance": round(new_balance, 2), "message": f"Added ${body.amount:.2f} to pool"}


@app.get("/api/v1/admin/users")
async def admin_list_users(
    search: Optional[str] = None,
    tier_filter: Optional[str] = None,
    user: dict = Depends(require_admin),
):
    """List all users with tier/usage info (admin only)"""
    async with db_pool.acquire() as conn:
        conditions = []
        params = []
        idx = 1

        if search:
            conditions.append(f"(p.email ILIKE ${idx} OR p.username ILIKE ${idx} OR p.full_name ILIKE ${idx})")
            params.append(f"%{search}%")
            idx += 1

        if tier_filter:
            conditions.append(f"COALESCE(t.tier, 'free') = ${idx}")
            params.append(tier_filter)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        rows = await conn.fetch(f"""
            SELECT
                p.id,
                p.email,
                p.username,
                p.full_name,
                COALESCE(t.tier, 'free') as tier,
                COALESCE(t.messages_today, 0) as messages_today,
                t.last_message_date,
                t.daily_limit as custom_daily_limit,
                t.model_override,
                p.created_at as profile_created_at,
                t.updated_at as last_active
            FROM profiles p
            LEFT JOIN user_tiers t ON p.id::text = t.user_id
            {where}
            ORDER BY t.updated_at DESC NULLS LAST
            LIMIT 200
        """, *params)

    default_free_model = "claude-haiku-4-5-20251001"
    default_pro_model = "claude-sonnet-4-6"

    users = []
    for r in rows:
        tier = r["tier"]
        messages_today = r["messages_today"]
        if r["last_message_date"] and r["last_message_date"] != date.today():
            messages_today = 0

        custom_limit = r["custom_daily_limit"]
        if custom_limit is not None:
            daily_limit = custom_limit
        elif tier == "pro":
            daily_limit = None
        else:
            daily_limit = 15

        default_model = default_pro_model if tier == "pro" else default_free_model
        effective_model = r["model_override"] or default_model

        users.append({
            "id": str(r["id"]),
            "email": r["email"],
            "username": r["username"],
            "full_name": r["full_name"],
            "tier": tier,
            "messages_today": messages_today,
            "daily_limit": daily_limit,
            "custom_daily_limit": custom_limit,
            "model_override": r["model_override"],
            "effective_model": effective_model,
            "last_message_date": r["last_message_date"].isoformat() if r["last_message_date"] else None,
            "profile_created_at": r["profile_created_at"].isoformat() if r["profile_created_at"] else None,
            "last_active": r["last_active"].isoformat() if r["last_active"] else None,
        })

    return users


@app.patch("/api/v1/admin/users/{user_id}")
async def admin_update_user(
    user_id: str,
    body: AdminUserUpdate,
    user: dict = Depends(require_admin),
):
    """Update a user's tier, daily limit, or model override (admin only)"""
    async with db_pool.acquire() as conn:
        # Build SET clauses
        sets = []
        params = [user_id]  # $1
        idx = 2

        tier_value = "free"  # default for UPSERT insert

        if body.tier is not None:
            if body.tier not in ("free", "pro"):
                raise HTTPException(status_code=400, detail="tier must be 'free' or 'pro'")
            sets.append(f"tier = ${idx}")
            params.append(body.tier)
            tier_value = body.tier
            idx += 1

        if body.daily_limit is not None:
            if body.daily_limit == -1:
                sets.append("daily_limit = NULL")
            else:
                sets.append(f"daily_limit = ${idx}")
                params.append(body.daily_limit)
                idx += 1

        if body.model_override is not None:
            if body.model_override == "":
                sets.append("model_override = NULL")
            else:
                sets.append(f"model_override = ${idx}")
                params.append(body.model_override)
                idx += 1

        if not sets:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_clause = ", ".join(sets)

        await conn.execute(f"""
            INSERT INTO user_tiers (user_id, tier)
            VALUES ($1, '{tier_value}')
            ON CONFLICT (user_id) DO UPDATE SET {update_clause}, updated_at = NOW()
        """, *params)

        # Return updated state
        row = await conn.fetchrow("""
            SELECT
                p.id, p.email, p.username, p.full_name,
                COALESCE(t.tier, 'free') as tier,
                COALESCE(t.messages_today, 0) as messages_today,
                t.last_message_date,
                t.daily_limit as custom_daily_limit,
                t.model_override,
                p.created_at as profile_created_at,
                t.updated_at as last_active
            FROM profiles p
            LEFT JOIN user_tiers t ON p.id::text = t.user_id
            WHERE p.id::text = $1
        """, user_id)

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        tier = row["tier"]
        default_model = "claude-sonnet-4-6" if tier == "pro" else "claude-haiku-4-5-20251001"

        return {
            "id": str(row["id"]),
            "email": row["email"],
            "username": row["username"],
            "full_name": row["full_name"],
            "tier": tier,
            "messages_today": row["messages_today"],
            "custom_daily_limit": row["custom_daily_limit"],
            "model_override": row["model_override"],
            "effective_model": row["model_override"] or default_model,
            "last_active": row["last_active"].isoformat() if row["last_active"] else None,
        }


# ============================================================================
# Casebook Lookup (instant search by case name)
# ============================================================================

_casebook_cache: Dict[str, Any] = {"data": None, "time": 0}
CASEBOOK_CACHE_TTL = 300  # 5 minutes

@app.get("/api/v1/casebook-cases")
async def get_casebook_cases():
    """Return all casebook-linked cases with subject data and brief availability."""
    now = time.time()
    if _casebook_cache["data"] and (now - _casebook_cache["time"]) < CASEBOOK_CACHE_TTL:
        return _casebook_cache["data"]

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.id, c.title, c.reporter_cite, c.decision_date,
                   ct.name as court_name,
                   CASE WHEN s.case_id IS NOT NULL THEN true ELSE false END as has_brief,
                   array_agg(DISTINCT cb.subject) FILTER (WHERE cb.subject IS NOT NULL) as subjects,
                   COALESCE((c.metadata->>'citation_count')::int, 0) as citation_count
            FROM cases c
            JOIN casebook_cases cc ON cc.case_id = c.id
            JOIN casebooks cb ON cc.casebook_id = cb.id
            LEFT JOIN ai_summaries s ON s.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            GROUP BY c.id, c.title, c.reporter_cite, c.decision_date, ct.name, s.case_id, c.metadata
            ORDER BY citation_count DESC, c.title
        """)

        # Build subject counts
        subject_counter: Dict[str, int] = {}
        for r in rows:
            if r["subjects"]:
                for subj in r["subjects"]:
                    subject_counter[subj] = subject_counter.get(subj, 0) + 1
        subject_counts = sorted(
            [{"subject": s, "count": c} for s, c in subject_counter.items()],
            key=lambda x: x["count"],
            reverse=True,
        )

    cases_list = [
        {
            "id": r["id"],
            "title": r["title"],
            "reporter_cite": r["reporter_cite"],
            "decision_date": r["decision_date"].isoformat() if r["decision_date"] else None,
            "court_name": r["court_name"],
            "has_brief": r["has_brief"],
            "subjects": r["subjects"] or [],
            "citation_count": r["citation_count"],
        }
        for r in rows
    ]

    result = {
        "cases": cases_list,
        "subject_counts": subject_counts,
        "total": len(cases_list),
    }
    _casebook_cache["data"] = result
    _casebook_cache["time"] = now
    return result


# ============================================================================
# Textbooks (Browse by Casebook)
# ============================================================================

_textbooks_cache: Dict[str, Any] = {"data": None, "time": 0}
TEXTBOOKS_CACHE_TTL = 300  # 5 minutes

@app.get("/api/v1/textbooks")
async def get_textbooks():
    """Return all textbooks with case counts and brief availability."""
    now = time.time()
    if _textbooks_cache["data"] and (now - _textbooks_cache["time"]) < TEXTBOOKS_CACHE_TTL:
        return _textbooks_cache["data"]

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT cb.id, cb.title, cb.edition, cb.authors, cb.subject,
                   cb.isbn, cb.year,
                   COUNT(DISTINCT cc.case_id) as case_count,
                   COUNT(DISTINCT s.case_id) as brief_count
            FROM casebooks cb
            LEFT JOIN casebook_cases cc ON cc.casebook_id = cb.id
            LEFT JOIN ai_summaries s ON s.case_id = cc.case_id
            WHERE cb.authors IS NOT NULL
            GROUP BY cb.id
            ORDER BY cb.subject, cb.title
        """)

    result = [
        {
            "id": r["id"],
            "title": r["title"],
            "edition": r["edition"],
            "authors": r["authors"],
            "subject": r["subject"],
            "isbn": r["isbn"],
            "year": r["year"],
            "case_count": r["case_count"],
            "brief_count": r["brief_count"],
        }
        for r in rows
    ]
    _textbooks_cache["data"] = result
    _textbooks_cache["time"] = now
    return result


_textbook_detail_cache: Dict[int, Dict[str, Any]] = {}
TEXTBOOK_DETAIL_CACHE_TTL = 300

@app.get("/api/v1/textbooks/{textbook_id}")
async def get_textbook_detail(textbook_id: int):
    """Return textbook metadata with all linked cases."""
    now = time.time()
    cached = _textbook_detail_cache.get(textbook_id)
    if cached and (now - cached["time"]) < TEXTBOOK_DETAIL_CACHE_TTL:
        return cached["data"]

    async with db_pool.acquire() as conn:
        # Get textbook metadata
        book = await conn.fetchrow("""
            SELECT id, title, edition, authors, subject, isbn, year
            FROM casebooks WHERE id = $1
        """, textbook_id)
        if not book:
            raise HTTPException(status_code=404, detail="Textbook not found")

        # Get cases via casebook_cases with brief availability
        cases = await conn.fetch("""
            SELECT cc.case_id as id, c.title, c.reporter_cite, c.decision_date,
                   ct.name as court_name,
                   CASE WHEN s.case_id IS NOT NULL THEN true ELSE false END as has_brief,
                   cc.chapter, cc.sort_order, cc.case_name_in_book
            FROM casebook_cases cc
            JOIN cases c ON cc.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            LEFT JOIN ai_summaries s ON s.case_id = c.id
            WHERE cc.casebook_id = $1
            ORDER BY cc.sort_order NULLS LAST, c.title
        """, textbook_id)

        # Get pending count
        pending = await conn.fetchval("""
            SELECT COUNT(*) FROM casebook_pending_imports
            WHERE casebook_id = $1 AND import_status = 'pending'
        """, textbook_id)

    result = {
        "id": book["id"],
        "title": book["title"],
        "edition": book["edition"],
        "authors": book["authors"],
        "subject": book["subject"],
        "isbn": book["isbn"],
        "year": book["year"],
        "cases": [
            {
                "id": r["id"],
                "title": r["title"],
                "reporter_cite": r["reporter_cite"],
                "decision_date": r["decision_date"].isoformat() if r["decision_date"] else None,
                "court_name": r["court_name"],
                "has_brief": r["has_brief"],
                "chapter": r["chapter"],
                "sort_order": r["sort_order"],
                "case_name_in_book": r["case_name_in_book"],
            }
            for r in cases
        ],
        "pending_count": pending or 0,
    }
    _textbook_detail_cache[textbook_id] = {"data": result, "time": now}
    return result


# ============================================================================
# Trending Cases (community engagement)
# ============================================================================

_trending_cache: Dict[str, Any] = {"data": None, "time": 0}
TRENDING_CACHE_TTL = 600  # 10 minutes

@app.get("/api/v1/trending-cases")
async def get_trending_cases():
    """Return cases ranked by community engagement (ratings + comments)."""
    now = time.time()
    if _trending_cache["data"] and (now - _trending_cache["time"]) < TRENDING_CACHE_TTL:
        return _trending_cache["data"]

    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.id, c.title, c.reporter_cite, c.decision_date,
                   ct.name as court_name,
                   CASE WHEN s.case_id IS NOT NULL THEN true ELSE false END as has_brief,
                   COALESCE(r.thumbs_up, 0) as thumbs_up,
                   COALESCE(r.thumbs_down, 0) as thumbs_down,
                   COALESCE(cm.comment_count, 0) as comment_count,
                   (COALESCE(r.thumbs_up, 0) * 2
                    + COALESCE(r.thumbs_down, 0) * 1
                    + COALESCE(cm.comment_count, 0) * 3) as engagement_score
            FROM cases c
            LEFT JOIN courts ct ON c.court_id = ct.id
            LEFT JOIN ai_summaries s ON s.case_id = c.id
            LEFT JOIN LATERAL (
                SELECT sr.case_id,
                       COUNT(*) FILTER (WHERE sr.rating = 1) as thumbs_up,
                       COUNT(*) FILTER (WHERE sr.rating = -1) as thumbs_down
                FROM public.summary_ratings sr
                WHERE sr.case_id = c.id
                GROUP BY sr.case_id
            ) r ON true
            LEFT JOIN LATERAL (
                SELECT co.case_id, COUNT(*) as comment_count
                FROM public.comments co
                WHERE co.case_id = c.id
                GROUP BY co.case_id
            ) cm ON true
            WHERE (COALESCE(r.thumbs_up, 0) * 2
                   + COALESCE(r.thumbs_down, 0) * 1
                   + COALESCE(cm.comment_count, 0) * 3) > 0
            ORDER BY engagement_score DESC
            LIMIT 8
        """)

    cases_list = [
        {
            "id": r["id"],
            "title": r["title"],
            "reporter_cite": r["reporter_cite"],
            "decision_date": r["decision_date"].isoformat() if r["decision_date"] else None,
            "court_name": r["court_name"],
            "has_brief": r["has_brief"],
            "thumbs_up": r["thumbs_up"],
            "thumbs_down": r["thumbs_down"],
            "comment_count": r["comment_count"],
            "engagement_score": r["engagement_score"],
        }
        for r in rows
    ]

    result = {"cases": cases_list}
    _trending_cache["data"] = result
    _trending_cache["time"] = now
    return result


# ============================================================================
# Search Cases (homepage search-first design)
# ============================================================================

@app.get("/api/v1/search-cases")
async def search_cases(q: str = "", limit: int = 50):
    """Search all cases by title or citation. Returns results sorted by citation count."""
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")

    pattern = f"%{q.strip()}%"
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.id, c.title, c.reporter_cite, c.decision_date,
                   ct.name as court_name,
                   CASE WHEN s.case_id IS NOT NULL THEN true ELSE false END as has_brief,
                   COALESCE((c.metadata->>'citation_count')::int, 0) as citation_count
            FROM cases c
            LEFT JOIN ai_summaries s ON s.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE c.title ILIKE $1 OR c.reporter_cite ILIKE $1
            ORDER BY citation_count DESC, c.title
            LIMIT $2
        """, pattern, min(limit, 100))

    return {
        "cases": [
            {
                "id": r["id"],
                "title": r["title"],
                "reporter_cite": r["reporter_cite"],
                "decision_date": r["decision_date"].isoformat() if r["decision_date"] else None,
                "court_name": r["court_name"],
                "has_brief": r["has_brief"],
                "citation_count": r["citation_count"],
            }
            for r in rows
        ]
    }


# ============================================================================
# Case Count (for homepage hero text)
# ============================================================================

_case_count_cache: Dict[str, Any] = {"count": None, "time": 0}
CASE_COUNT_CACHE_TTL = 600  # 10 minutes

@app.get("/api/v1/case-count")
async def get_case_count():
    """Return total number of cases in the database. Cached for 10 minutes."""
    now = time.time()
    if _case_count_cache["count"] is not None and (now - _case_count_cache["time"]) < CASE_COUNT_CACHE_TTL:
        return {"count": _case_count_cache["count"]}

    async with db_pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM cases")

    _case_count_cache["count"] = count
    _case_count_cache["time"] = now
    return {"count": count}


# ============================================================================
# Legal Texts (Constitution, FRCP, Federal Statutes)
# ============================================================================

@app.get("/api/v1/legal-texts")
async def list_legal_documents():
    """List all legal text documents with item counts."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT d.id, d.title, d.doc_type, d.metadata,
                   COUNT(i.id) as item_count
            FROM legal_documents d
            LEFT JOIN legal_text_items i ON i.document_id = d.id
            GROUP BY d.id
            ORDER BY d.id
        """)
    return {
        "documents": [
            {
                "id": r["id"],
                "title": r["title"],
                "doc_type": r["doc_type"],
                "metadata": json.loads(r["metadata"]) if isinstance(r["metadata"], str) else r["metadata"],
                "item_count": r["item_count"],
            }
            for r in rows
        ]
    }


@app.get("/api/v1/legal-texts/search")
async def search_legal_texts(q: str, doc_id: Optional[str] = None, limit: int = 50):
    """Full-text search across all legal text items."""
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")

    async with db_pool.acquire() as conn:
        if doc_id:
            rows = await conn.fetch("""
                SELECT i.id, i.document_id, i.slug, i.title, i.citation, i.number,
                       ts_rank(to_tsvector('english', i.body), plainto_tsquery('english', $1)) as rank,
                       ts_headline('english', i.body, plainto_tsquery('english', $1),
                                   'StartSel=<mark>, StopSel=</mark>, MaxWords=60, MinWords=20') as snippet
                FROM legal_text_items i
                WHERE i.document_id = $2
                  AND to_tsvector('english', i.body) @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $3
            """, q, doc_id, limit)
        else:
            rows = await conn.fetch("""
                SELECT i.id, i.document_id, i.slug, i.title, i.citation, i.number,
                       ts_rank(to_tsvector('english', i.body), plainto_tsquery('english', $1)) as rank,
                       ts_headline('english', i.body, plainto_tsquery('english', $1),
                                   'StartSel=<mark>, StopSel=</mark>, MaxWords=60, MinWords=20') as snippet
                FROM legal_text_items i
                WHERE to_tsvector('english', i.body) @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $2
            """, q, limit)

    return {
        "results": [
            {
                "id": r["id"],
                "document_id": r["document_id"],
                "slug": r["slug"],
                "title": r["title"],
                "citation": r["citation"],
                "number": r["number"],
                "rank": float(r["rank"]),
                "snippet": r["snippet"],
            }
            for r in rows
        ],
        "count": len(rows),
        "query": q,
    }


@app.get("/api/v1/legal-texts/{doc_id}")
async def get_legal_document(doc_id: str):
    """Get a legal document with all its items."""
    async with db_pool.acquire() as conn:
        doc = await conn.fetchrow(
            "SELECT * FROM legal_documents WHERE id = $1", doc_id
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        items = await conn.fetch("""
            SELECT id, slug, title, citation, number, sort_order
            FROM legal_text_items
            WHERE document_id = $1
            ORDER BY sort_order
        """, doc_id)

    return {
        "id": doc["id"],
        "title": doc["title"],
        "doc_type": doc["doc_type"],
        "metadata": json.loads(doc["metadata"]) if isinstance(doc["metadata"], str) else doc["metadata"],
        "items": [
            {
                "id": r["id"],
                "slug": r["slug"],
                "title": r["title"],
                "citation": r["citation"],
                "number": r["number"],
                "sort_order": r["sort_order"],
            }
            for r in items
        ],
    }


@app.get("/api/v1/legal-texts/{doc_id}/{slug}")
async def get_legal_text_item(doc_id: str, slug: str):
    """Get a single legal text item with full content."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT i.*, d.title as doc_title
            FROM legal_text_items i
            JOIN legal_documents d ON d.id = i.document_id
            WHERE i.document_id = $1 AND i.slug = $2
        """, doc_id, slug)

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "doc_title": row["doc_title"],
        "slug": row["slug"],
        "title": row["title"],
        "citation": row["citation"],
        "number": row["number"],
        "body": row["body"],
        "content": json.loads(row["content"]) if isinstance(row["content"], str) else row["content"],
        "sort_order": row["sort_order"],
    }


def _build_ilike_patterns(doc_id: str, slug: str) -> list[str]:
    """Build ILIKE search patterns from a legal text slug."""
    if doc_id == "frcp":
        # rule-12 → '%Rule 12%'
        num = slug.replace("rule-", "")
        return [f"%Rule {num}%"]

    elif doc_id == "federal_statutes":
        # 28-usc-1332 → '%28 U.S.C.%' AND '%1332%'
        parts = slug.split("-")
        if len(parts) >= 3 and parts[1] == "usc":
            title_num = parts[0]
            section = "-".join(parts[2:])
            return [f"%{title_num} U.S.C.%", f"%{section}%"]
        return [f"%{slug}%"]

    elif doc_id == "constitution":
        # amendment-14 → multiple patterns (OR logic)
        if slug.startswith("amendment-"):
            num = slug.replace("amendment-", "")
            ordinals = {
                "1": "First", "2": "Second", "3": "Third", "4": "Fourth",
                "5": "Fifth", "6": "Sixth", "7": "Seventh", "8": "Eighth",
                "9": "Ninth", "10": "Tenth", "11": "Eleventh", "12": "Twelfth",
                "13": "Thirteenth", "14": "Fourteenth", "15": "Fifteenth",
                "16": "Sixteenth", "17": "Seventeenth", "18": "Eighteenth",
                "19": "Nineteenth", "20": "Twentieth", "21": "Twenty-first",
                "22": "Twenty-second", "23": "Twenty-third", "24": "Twenty-fourth",
                "25": "Twenty-fifth", "26": "Twenty-sixth", "27": "Twenty-seventh",
            }
            roman = {
                "1": "I", "2": "II", "3": "III", "4": "IV", "5": "V",
                "6": "VI", "7": "VII", "8": "VIII", "9": "IX", "10": "X",
                "11": "XI", "12": "XII", "13": "XIII", "14": "XIV", "15": "XV",
                "16": "XVI", "17": "XVII", "18": "XVIII", "19": "XIX", "20": "XX",
                "21": "XXI", "22": "XXII", "23": "XXIII", "24": "XXIV", "25": "XXV",
                "26": "XXVI", "27": "XXVII",
            }
            patterns = [f"%Amendment {roman.get(num, num)}%"]
            if num in ordinals:
                patterns.append(f"%{ordinals[num]} Amendment%")
            patterns.append(f"%{num}th Amendment%")
            return patterns
        elif slug.startswith("article-"):
            num = slug.replace("article-", "")
            return [f"%Article {num}%"]
        return [f"%{slug}%"]

    return [f"%{slug}%"]


@app.get("/api/v1/legal-texts/{doc_id}/{slug}/cases")
async def get_legal_text_cases(doc_id: str, slug: str, limit: int = 20):
    """Find cases whose AI summaries mention a legal text (rule, statute, or amendment)."""
    patterns = _build_ilike_patterns(doc_id, slug)

    # Build WHERE clause: for constitution amendments, patterns are OR'd;
    # for statutes like "28-usc-1332", patterns are AND'd (need both title and section)
    if doc_id == "constitution":
        where_parts = [f"s.summary ILIKE ${i+1}" for i in range(len(patterns))]
        where_clause = " OR ".join(where_parts)
    elif doc_id == "federal_statutes" and len(patterns) > 1:
        where_parts = [f"s.summary ILIKE ${i+1}" for i in range(len(patterns))]
        where_clause = " AND ".join(where_parts)
    else:
        where_clause = "s.summary ILIKE $1"

    query = f"""
        SELECT c.id, c.title, c.decision_date,
               ct.name as court_name,
               COALESCE((c.metadata->>'citation_count')::int, 0) as citation_count,
               s.summary as summary_text
        FROM ai_summaries s
        JOIN cases c ON c.id = s.case_id
        LEFT JOIN courts ct ON ct.id = c.court_id
        WHERE {where_clause}
        ORDER BY COALESCE((c.metadata->>'citation_count')::int, 0) DESC
        LIMIT ${len(patterns) + 1}
    """

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *patterns, limit)

    results = []
    for row in rows:
        # Extract snippet around first match
        summary = row["summary_text"] or ""
        snippet = ""
        lower_summary = summary.lower()
        for p in patterns:
            search_term = p.strip("%").lower()
            idx = lower_summary.find(search_term)
            if idx != -1:
                start = max(0, idx - 60)
                end = min(len(summary), idx + len(search_term) + 90)
                raw = summary[start:end].strip()
                if start > 0:
                    raw = "..." + raw
                if end < len(summary):
                    raw = raw + "..."
                # Wrap match in <em> for highlighting
                match_text = summary[idx:idx + len(search_term)]
                snippet = raw.replace(match_text, f"<em>{match_text}</em>", 1)
                break

        year = ""
        if row["decision_date"]:
            year = str(row["decision_date"].year) if hasattr(row["decision_date"], "year") else str(row["decision_date"])[:4]

        results.append({
            "id": row["id"],
            "title": row["title"],
            "court_name": row["court_name"],
            "year": year,
            "citation_count": row["citation_count"],
            "snippet": snippet,
        })

    return {"results": results, "count": len(results)}


# ============================================================================
# Study Session Engine - Mindmap Upload & Session Management
# ============================================================================

def walk_mindmap_tree(node, parent_id=None, depth=0, counter=[0]):
    """Recursively flatten a mindmap tree into node rows."""
    nodes = []
    node_id = node.get("id", f"node_{counter[0]}")
    text = node.get("text", node.get("name", ""))
    children = node.get("children", [])

    case_pattern = re.compile(r'([A-Z][a-zA-Z.\']+\s+v\.?\s+[A-Z][a-zA-Z.\',& ]+)')
    rule_pattern = re.compile(r'(?:Rule|FRCP)\s+(\d+(?:\([a-z]\)(?:\(\d+\))?)?)')

    case_matches = case_pattern.findall(text)
    rule_matches = rule_pattern.findall(text)

    nodes.append({
        "node_id": node_id,
        "parent_node_id": parent_id,
        "depth": depth,
        "text": text,
        "is_leaf": len(children) == 0,
        "case_names": case_matches,
        "rule_numbers": rule_matches,
        "sort_order": counter[0],
    })
    counter[0] += 1

    for child in children:
        nodes.extend(walk_mindmap_tree(child, node_id, depth + 1, counter))

    return nodes


@app.post("/api/v1/study/mindmaps/upload")
async def upload_mindmap(
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
):
    """Upload and parse a .mindmap.json file"""
    filename = file.filename or "untitled"
    if not filename.endswith(".mindmap.json") and not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .mindmap.json or .json files are supported")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size limit is 10MB")

    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    name = data.get("name", filename.replace(".mindmap.json", "").replace(".json", ""))
    root = data.get("root", data)

    # Flatten tree
    counter = [0]
    flat_nodes = walk_mindmap_tree(root, counter=counter)
    node_count = len(flat_nodes)
    max_depth = max(n["depth"] for n in flat_nodes) if flat_nodes else 0

    user_id = user["id"]

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Insert mindmap
            row = await conn.fetchrow("""
                INSERT INTO mindmaps (user_id, name, tree, node_count, max_depth)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, created_at
            """, user_id, name, json.dumps(data), node_count, max_depth)
            mindmap_id = row["id"]

            # Resolve case and rule references, then insert nodes
            for node in flat_nodes:
                case_refs = []
                for case_name in node["case_names"]:
                    case_row = await conn.fetchrow(
                        "SELECT id, title FROM cases WHERE title ILIKE '%' || $1 || '%' LIMIT 1",
                        case_name.strip()
                    )
                    if case_row:
                        case_refs.append({"name": case_name, "case_id": case_row["id"]})
                    else:
                        case_refs.append({"name": case_name, "case_id": None})

                rule_refs = []
                for rule_num in node["rule_numbers"]:
                    main_num = rule_num.split("(")[0]
                    rule_row = await conn.fetchrow(
                        "SELECT id, slug, title FROM legal_text_items WHERE document_id = 'frcp' AND number = $1 LIMIT 1",
                        main_num
                    )
                    if rule_row:
                        rule_refs.append({"ref": rule_num, "item_id": rule_row["id"], "slug": rule_row["slug"]})
                    else:
                        rule_refs.append({"ref": rule_num, "item_id": None, "slug": None})

                await conn.execute("""
                    INSERT INTO mindmap_nodes (mindmap_id, node_id, parent_node_id, depth, text, is_leaf, case_refs, rule_refs, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, mindmap_id, node["node_id"], node["parent_node_id"], node["depth"],
                    node["text"], node["is_leaf"], json.dumps(case_refs), json.dumps(rule_refs), node["sort_order"])

    return {
        "id": mindmap_id,
        "name": name,
        "node_count": node_count,
        "max_depth": max_depth,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def walk_and_save_nodes(conn, mindmap_id, tree_data):
    """Shared helper: flatten tree, resolve refs, insert mindmap_nodes rows. Returns (node_count, max_depth)."""
    # v2: editor + community sharing support
    root = tree_data.get("root", tree_data)
    counter = [0]
    flat_nodes = walk_mindmap_tree(root, counter=counter)
    node_count = len(flat_nodes)
    max_depth = max(n["depth"] for n in flat_nodes) if flat_nodes else 0

    for node in flat_nodes:
        case_refs = []
        for case_name in node["case_names"]:
            case_row = await conn.fetchrow(
                "SELECT id, title FROM cases WHERE title ILIKE '%' || $1 || '%' LIMIT 1",
                case_name.strip()
            )
            if case_row:
                case_refs.append({"name": case_name, "case_id": case_row["id"]})
            else:
                case_refs.append({"name": case_name, "case_id": None})

        rule_refs = []
        for rule_num in node["rule_numbers"]:
            main_num = rule_num.split("(")[0]
            rule_row = await conn.fetchrow(
                "SELECT id, slug, title FROM legal_text_items WHERE document_id = 'frcp' AND number = $1 LIMIT 1",
                main_num
            )
            if rule_row:
                rule_refs.append({"ref": rule_num, "item_id": rule_row["id"], "slug": rule_row["slug"]})
            else:
                rule_refs.append({"ref": rule_num, "item_id": None, "slug": None})

        await conn.execute("""
            INSERT INTO mindmap_nodes (mindmap_id, node_id, parent_node_id, depth, text, is_leaf, case_refs, rule_refs, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, mindmap_id, node["node_id"], node["parent_node_id"], node["depth"],
            node["text"], node["is_leaf"], json.dumps(case_refs), json.dumps(rule_refs), node["sort_order"])

    return node_count, max_depth


class MindmapSave(BaseModel):
    name: str
    tree: dict


@app.post("/api/v1/study/mindmaps/save")
async def save_new_mindmap(body: MindmapSave, user: dict = Depends(require_auth)):
    """Create a new mindmap from editor (JSON body instead of file upload)"""
    user_id = user["id"]
    tree_data = body.tree

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow("""
                INSERT INTO mindmaps (user_id, name, tree, node_count, max_depth)
                VALUES ($1, $2, $3, 0, 0)
                RETURNING id, created_at
            """, user_id, body.name, json.dumps(tree_data))
            mindmap_id = row["id"]

            node_count, max_depth = await walk_and_save_nodes(conn, mindmap_id, tree_data)

            await conn.execute(
                "UPDATE mindmaps SET node_count = $1, max_depth = $2 WHERE id = $3",
                node_count, max_depth, mindmap_id
            )

    return {
        "id": mindmap_id,
        "name": body.name,
        "node_count": node_count,
        "max_depth": max_depth,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.put("/api/v1/study/mindmaps/{mindmap_id}")
async def update_mindmap(mindmap_id: int, body: MindmapSave, user: dict = Depends(require_auth)):
    """Save edited mindmap — re-flattens tree, preserves node_progress"""
    user_id = user["id"]

    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM mindmaps WHERE id = $1 AND user_id = $2", mindmap_id, user_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Mindmap not found")

        async with conn.transaction():
            # Delete old nodes (node_progress is keyed separately, not cascade-deleted here)
            await conn.execute("DELETE FROM mindmap_nodes WHERE mindmap_id = $1", mindmap_id)

            # Re-insert from new tree
            tree_data = body.tree
            node_count, max_depth = await walk_and_save_nodes(conn, mindmap_id, tree_data)

            await conn.execute("""
                UPDATE mindmaps SET name = $1, tree = $2, node_count = $3, max_depth = $4, updated_at = NOW()
                WHERE id = $5
            """, body.name, json.dumps(tree_data), node_count, max_depth, mindmap_id)

    return {"ok": True, "node_count": node_count, "max_depth": max_depth}


class MindmapGenerate(BaseModel):
    topic: str
    subject: Optional[str] = None
    depth: Optional[int] = 3


@app.post("/api/v1/study/mindmaps/generate")
async def generate_mindmap(body: MindmapGenerate, user: dict = Depends(require_auth)):
    """AI-generate a mindmap tree from a topic prompt"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    depth = max(2, min(4, body.depth or 3))
    subject_ctx = f" in the context of {body.subject}" if body.subject else ""

    system_prompt = f"""You are a law school study aid. Generate a hierarchical mind map for studying.
Output ONLY valid JSON with this exact structure — no markdown fences, no explanation:
{{"version":1,"name":"Topic Name","root":{{"id":"node_1","text":"Topic Name","collapsed":false,"children":[{{"id":"node_2","text":"Subtopic","collapsed":false,"children":[]}}]}}}}

Rules:
- Create a tree with up to {depth} levels deep
- Each node needs a unique id like "node_1", "node_2", etc.
- Include key cases (e.g. "Erie Railroad v. Tompkins") and rules (e.g. "Rule 12(b)(6)") in node text where relevant
- Leaf nodes should be specific enough to quiz on
- Every node must have: id, text, collapsed (false), children (array)
- Target 15-30 total nodes for depth 3"""

    user_prompt = f"Create a mind map for: {body.topic}{subject_ctx}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=30.0,
            )

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"AI service error: {response.status_code}")

        data = response.json()
        raw_text = data["content"][0]["text"]

        # Parse JSON — handle potential markdown fences
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        tree = json.loads(cleaned)

        # Validate structure
        root = tree.get("root", tree)
        if not root.get("id") or not root.get("text"):
            raise HTTPException(status_code=502, detail="AI generated invalid mindmap structure")

        # Ensure proper structure
        if "root" not in tree:
            tree = {"version": 1, "name": root.get("text", body.topic), "root": root}

        return tree

    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI returned invalid JSON. Please try again.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI generation timed out. Please try again.")


@app.get("/api/v1/study/mindmaps/community")
async def community_mindmaps(subject: Optional[str] = None):
    """Browse public mindmaps shared by the community"""
    async with db_pool.acquire() as conn:
        if subject:
            rows = await conn.fetch("""
                SELECT m.id, m.name, m.node_count, m.max_depth, m.subject, m.created_at,
                       p.username, p.full_name
                FROM mindmaps m
                LEFT JOIN profiles p ON m.user_id = p.id
                WHERE m.is_public = true AND m.subject = $1
                ORDER BY m.created_at DESC
                LIMIT 50
            """, subject)
        else:
            rows = await conn.fetch("""
                SELECT m.id, m.name, m.node_count, m.max_depth, m.subject, m.created_at,
                       p.username, p.full_name
                FROM mindmaps m
                LEFT JOIN profiles p ON m.user_id = p.id
                WHERE m.is_public = true
                ORDER BY m.created_at DESC
                LIMIT 50
            """)

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "node_count": r["node_count"],
            "max_depth": r["max_depth"],
            "subject": r["subject"],
            "author": r["username"] or r["full_name"] or "Anonymous",
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@app.post("/api/v1/study/mindmaps/{mindmap_id}/clone")
async def clone_mindmap(mindmap_id: int, user: dict = Depends(require_auth)):
    """Clone a public mindmap to the current user's account"""
    user_id = user["id"]

    async with db_pool.acquire() as conn:
        source = await conn.fetchrow(
            "SELECT id, name, tree, is_public, user_id FROM mindmaps WHERE id = $1",
            mindmap_id
        )
        if not source:
            raise HTTPException(status_code=404, detail="Mindmap not found")
        if not source["is_public"] and source["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="This mindmap is not public")

        tree_data = json.loads(source["tree"]) if isinstance(source["tree"], str) else source["tree"]

        async with conn.transaction():
            row = await conn.fetchrow("""
                INSERT INTO mindmaps (user_id, name, tree, node_count, max_depth)
                VALUES ($1, $2, $3, 0, 0)
                RETURNING id, created_at
            """, user_id, source["name"], source["tree"] if isinstance(source["tree"], str) else json.dumps(tree_data))
            new_id = row["id"]

            node_count, max_depth = await walk_and_save_nodes(conn, new_id, tree_data)

            await conn.execute(
                "UPDATE mindmaps SET node_count = $1, max_depth = $2 WHERE id = $3",
                node_count, max_depth, new_id
            )

    return {
        "id": new_id,
        "name": source["name"],
        "node_count": node_count,
        "max_depth": max_depth,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


class MindmapShare(BaseModel):
    is_public: bool
    subject: Optional[str] = None


@app.patch("/api/v1/study/mindmaps/{mindmap_id}/share")
async def toggle_mindmap_sharing(mindmap_id: int, body: MindmapShare, user: dict = Depends(require_auth)):
    """Toggle public sharing and set subject for a mindmap"""
    user_id = user["id"]

    async with db_pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE mindmaps SET is_public = $1, subject = $2, updated_at = NOW()
            WHERE id = $3 AND user_id = $4
        """, body.is_public, body.subject, mindmap_id, user_id)
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Mindmap not found")

    return {"ok": True}


@app.get("/api/v1/study/mindmaps")
async def list_mindmaps(user: dict = Depends(require_auth)):
    """List user's mindmaps with mastery counts"""
    user_id = user["id"]
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT m.id, m.name, m.node_count, m.max_depth, m.created_at,
                   m.is_public, m.subject,
                   COALESCE(p.mastered, 0) as nodes_mastered
            FROM mindmaps m
            LEFT JOIN (
                SELECT mindmap_id, COUNT(*) as mastered
                FROM node_progress
                WHERE user_id = $1 AND mastery = 'mastered'
                GROUP BY mindmap_id
            ) p ON p.mindmap_id = m.id
            WHERE m.user_id = $1
            ORDER BY m.created_at DESC
        """, user_id)
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "node_count": r["node_count"],
            "max_depth": r["max_depth"],
            "nodes_mastered": r["nodes_mastered"],
            "is_public": r["is_public"] or False,
            "subject": r["subject"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@app.get("/api/v1/study/mindmaps/{mindmap_id}")
async def get_mindmap(mindmap_id: int, user: dict = Depends(require_auth)):
    """Get full mindmap with node progress overlay"""
    user_id = user["id"]
    async with db_pool.acquire() as conn:
        mm = await conn.fetchrow(
            "SELECT id, name, tree, node_count, max_depth, created_at FROM mindmaps WHERE id = $1 AND user_id = $2",
            mindmap_id, user_id
        )
        if not mm:
            raise HTTPException(status_code=404, detail="Mindmap not found")

        nodes = await conn.fetch("""
            SELECT n.node_id, n.parent_node_id, n.depth, n.text, n.is_leaf, n.case_refs, n.rule_refs, n.sort_order,
                   COALESCE(p.mastery, 'unseen') as mastery, COALESCE(p.correct_streak, 0) as correct_streak,
                   COALESCE(p.total_attempts, 0) as total_attempts
            FROM mindmap_nodes n
            LEFT JOIN node_progress p ON p.mindmap_id = n.mindmap_id AND p.node_id = n.node_id AND p.user_id = $2
            WHERE n.mindmap_id = $1
            ORDER BY n.sort_order
        """, mindmap_id, user_id)

    return {
        "id": mm["id"],
        "name": mm["name"],
        "tree": json.loads(mm["tree"]) if isinstance(mm["tree"], str) else mm["tree"],
        "node_count": mm["node_count"],
        "max_depth": mm["max_depth"],
        "created_at": mm["created_at"].isoformat() if mm["created_at"] else None,
        "nodes": [
            {
                "node_id": n["node_id"],
                "parent_node_id": n["parent_node_id"],
                "depth": n["depth"],
                "text": n["text"],
                "is_leaf": n["is_leaf"],
                "case_refs": json.loads(n["case_refs"]) if isinstance(n["case_refs"], str) else n["case_refs"],
                "rule_refs": json.loads(n["rule_refs"]) if isinstance(n["rule_refs"], str) else n["rule_refs"],
                "sort_order": n["sort_order"],
                "mastery": n["mastery"],
                "correct_streak": n["correct_streak"],
                "total_attempts": n["total_attempts"],
            }
            for n in nodes
        ],
    }


@app.delete("/api/v1/study/mindmaps/{mindmap_id}")
async def delete_mindmap(mindmap_id: int, user: dict = Depends(require_auth)):
    """Delete a mindmap and all associated data"""
    user_id = user["id"]
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM mindmaps WHERE id = $1 AND user_id = $2", mindmap_id, user_id
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Mindmap not found")
    return {"ok": True}


async def get_quizzable_nodes(conn, mindmap_id, user_id, branch_node_id=None):
    """Get unmastered quizzable nodes in DFS order, optionally scoped to a branch."""
    if branch_node_id:
        # Get all descendants of the branch node
        nodes = await conn.fetch("""
            WITH RECURSIVE descendants AS (
                SELECT node_id, parent_node_id, depth, text, is_leaf, case_refs, rule_refs, sort_order
                FROM mindmap_nodes WHERE mindmap_id = $1 AND node_id = $2
                UNION ALL
                SELECT n.node_id, n.parent_node_id, n.depth, n.text, n.is_leaf, n.case_refs, n.rule_refs, n.sort_order
                FROM mindmap_nodes n
                INNER JOIN descendants d ON n.parent_node_id = d.node_id AND n.mindmap_id = $1
            )
            SELECT d.*, COALESCE(p.mastery, 'unseen') as mastery
            FROM descendants d
            LEFT JOIN node_progress p ON p.mindmap_id = $1 AND p.node_id = d.node_id AND p.user_id = $3
            WHERE (d.is_leaf = true OR length(d.text) > 30)
            ORDER BY d.sort_order
        """, mindmap_id, branch_node_id, user_id)
    else:
        nodes = await conn.fetch("""
            SELECT n.node_id, n.parent_node_id, n.depth, n.text, n.is_leaf, n.case_refs, n.rule_refs, n.sort_order,
                   COALESCE(p.mastery, 'unseen') as mastery
            FROM mindmap_nodes n
            LEFT JOIN node_progress p ON p.mindmap_id = n.mindmap_id AND p.node_id = n.node_id AND p.user_id = $2
            WHERE n.mindmap_id = $1 AND (n.is_leaf = true OR length(n.text) > 30)
            ORDER BY n.sort_order
        """, mindmap_id, user_id)
    return nodes


async def get_node_context(conn, mindmap_id, node_id):
    """Get parent chain and children for a node."""
    node = await conn.fetchrow(
        "SELECT * FROM mindmap_nodes WHERE mindmap_id = $1 AND node_id = $2",
        mindmap_id, node_id
    )
    if not node:
        return None, [], [], []

    # Get parent chain (breadcrumb)
    breadcrumb = []
    current_parent = node["parent_node_id"]
    while current_parent:
        parent = await conn.fetchrow(
            "SELECT node_id, text, parent_node_id FROM mindmap_nodes WHERE mindmap_id = $1 AND node_id = $2",
            mindmap_id, current_parent
        )
        if parent:
            breadcrumb.insert(0, parent["text"])
            current_parent = parent["parent_node_id"]
        else:
            break

    # Get children
    children = await conn.fetch(
        "SELECT text FROM mindmap_nodes WHERE mindmap_id = $1 AND parent_node_id = $2 ORDER BY sort_order",
        mindmap_id, node_id
    )
    children_texts = [c["text"] for c in children]

    return node, breadcrumb, children_texts, []


async def generate_question_via_claude(node_text, breadcrumb, children_texts, mode, case_context="", rule_context=""):
    """Generate a study question using Claude API."""
    mode_instructions = {
        "quiz": "Ask a direct recall question about this concept. Be specific.",
        "story": "Ask the student to tell you the story of this concept — what happened, who was involved, what was decided.",
        "analogy": "Frame this concept using an everyday analogy. Ask the student to explain it back using that analogy.",
        "hypo": "You're setting up a hypothetical. Create a short fact pattern (2-3 sentences) and ask the student to apply this concept.",
        "go_deeper": "The student is doing well. Ask a more challenging question that connects this concept to related topics or edge cases.",
    }

    instruction = mode_instructions.get(mode, mode_instructions["quiz"])

    prompt = f"""You are quizzing a law student with ADHD. Keep your question under 50 words. Be direct and engaging.

Topic path: {' > '.join(breadcrumb)}
Current concept: {node_text}
{f'Subtopics: {", ".join(children_texts)}' if children_texts else ''}
{case_context}
{rule_context}

Mode: {instruction}

Generate ONE question only. No preamble."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30.0,
        )

    if response.status_code != 200:
        return f"Explain the key aspects of: {node_text}"

    result = response.json()
    for block in result.get("content", []):
        if block.get("type") == "text":
            return block["text"]
    return f"Explain the key aspects of: {node_text}"


async def get_case_and_rule_context(conn, node):
    """Fetch case brief and rule text context for a node."""
    case_context = ""
    rule_context = ""

    case_refs = json.loads(node["case_refs"]) if isinstance(node["case_refs"], str) else (node["case_refs"] or [])
    rule_refs = json.loads(node["rule_refs"]) if isinstance(node["rule_refs"], str) else (node["rule_refs"] or [])

    for ref in case_refs:
        if ref.get("case_id"):
            brief = await conn.fetchrow(
                "SELECT summary FROM ai_summaries WHERE case_id = $1 LIMIT 1",
                ref["case_id"]
            )
            if brief and brief["summary"]:
                case_context += f"\nCase brief for {ref['name']}:\n{brief['summary'][:500]}\n"

    for ref in rule_refs:
        if ref.get("item_id"):
            rule = await conn.fetchrow(
                "SELECT title, body FROM legal_text_items WHERE id = $1",
                ref["item_id"]
            )
            if rule:
                body = rule["body"] or ""
                rule_context += f"\nRule text - {rule['title']}:\n{body[:500]}\n"

    return case_context, rule_context


@app.post("/api/v1/study/session/start")
async def start_study_session(body: SessionStart, user: dict = Depends(require_auth)):
    """Start or resume a study session on a mindmap"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    user_id = user["id"]
    mindmap_id = body.mindmap_id

    async with db_pool.acquire() as conn:
        # Verify mindmap ownership
        mm = await conn.fetchrow(
            "SELECT id, name FROM mindmaps WHERE id = $1 AND user_id = $2",
            mindmap_id, user_id
        )
        if not mm:
            raise HTTPException(status_code=404, detail="Mindmap not found")

        # Check for active session
        existing = await conn.fetchrow(
            "SELECT id, current_node_id, current_question, mode, streak, max_streak, nodes_visited, nodes_mastered, total_correct, total_incorrect FROM study_sessions WHERE user_id = $1 AND mindmap_id = $2 AND session_state = 'active'",
            user_id, mindmap_id
        )

        if existing and existing["current_question"]:
            # Resume existing session
            node, breadcrumb, children_texts, _ = await get_node_context(conn, mindmap_id, existing["current_node_id"])

            # Count total quizzable nodes
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM mindmap_nodes
                WHERE mindmap_id = $1 AND (is_leaf = true OR length(text) > 30)
            """, mindmap_id)

            return {
                "session_id": existing["id"],
                "resumed": True,
                "current_node_id": existing["current_node_id"],
                "question": existing["current_question"],
                "breadcrumb": breadcrumb,
                "mode": existing["mode"],
                "streak": existing["streak"],
                "max_streak": existing["max_streak"],
                "nodes_visited": existing["nodes_visited"],
                "nodes_mastered": existing["nodes_mastered"],
                "total_correct": existing["total_correct"],
                "total_incorrect": existing["total_incorrect"],
                "total_nodes": total,
                "node_text": node["text"] if node else "",
                "case_refs": json.loads(node["case_refs"]) if node and isinstance(node["case_refs"], str) else (node["case_refs"] if node else []),
                "rule_refs": json.loads(node["rule_refs"]) if node and isinstance(node["rule_refs"], str) else (node["rule_refs"] if node else []),
            }

        # Find first unmastered quizzable node
        quizzable = await get_quizzable_nodes(conn, mindmap_id, user_id, body.branch_node_id)
        unmastered = [n for n in quizzable if n["mastery"] != "mastered"]

        if not unmastered:
            return {"session_id": None, "completed": True, "message": "All nodes mastered!"}

        first_node = unmastered[0]
        total = len(quizzable)

        # Get context and generate question
        node, breadcrumb, children_texts, _ = await get_node_context(conn, mindmap_id, first_node["node_id"])
        case_context, rule_context = await get_case_and_rule_context(conn, node)

        question = await generate_question_via_claude(
            first_node["text"], breadcrumb, children_texts, "quiz", case_context, rule_context
        )

        # Create session
        if existing:
            # Update existing paused session
            await conn.execute("""
                UPDATE study_sessions SET session_state = 'active', current_node_id = $2, current_question = $3, last_activity_at = NOW()
                WHERE id = $1
            """, existing["id"], first_node["node_id"], question)
            session_id = existing["id"]
        else:
            row = await conn.fetchrow("""
                INSERT INTO study_sessions (user_id, mindmap_id, current_node_id, current_question, branch_node_id)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, user_id, mindmap_id, first_node["node_id"], question, body.branch_node_id)
            session_id = row["id"]

        mastered_count = await conn.fetchval(
            "SELECT COUNT(*) FROM node_progress WHERE user_id = $1 AND mindmap_id = $2 AND mastery = 'mastered'",
            user_id, mindmap_id
        )

    return {
        "session_id": session_id,
        "resumed": False,
        "current_node_id": first_node["node_id"],
        "question": question,
        "breadcrumb": breadcrumb,
        "mode": "quiz",
        "streak": 0,
        "max_streak": 0,
        "nodes_visited": 0,
        "nodes_mastered": mastered_count,
        "total_correct": 0,
        "total_incorrect": 0,
        "total_nodes": total,
        "node_text": first_node["text"],
        "case_refs": json.loads(first_node["case_refs"]) if isinstance(first_node["case_refs"], str) else (first_node["case_refs"] or []),
        "rule_refs": json.loads(first_node["rule_refs"]) if isinstance(first_node["rule_refs"], str) else (first_node["rule_refs"] or []),
    }


@app.post("/api/v1/study/session/{session_id}/respond")
async def session_respond(session_id: int, body: SessionRespond, user: dict = Depends(require_auth)):
    """Evaluate answer, update progress, generate next question. Returns SSE stream."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    user_id = user["id"]

    # Check community pool (session respond always uses site key)
    if not await check_pool_available(user_id):
        raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)

    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            "SELECT * FROM study_sessions WHERE id = $1 AND user_id = $2 AND session_state = 'active'",
            session_id, user_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Active session not found")

        mindmap_id = session["mindmap_id"]
        current_node_id = session["current_node_id"]

        # Get current node context
        node, breadcrumb, children_texts, _ = await get_node_context(conn, mindmap_id, current_node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Current node not found")

        case_context, rule_context = await get_case_and_rule_context(conn, node)

        # Get node refs for response
        node_case_refs = json.loads(node["case_refs"]) if isinstance(node["case_refs"], str) else (node["case_refs"] or [])
        node_rule_refs = json.loads(node["rule_refs"]) if isinstance(node["rule_refs"], str) else (node["rule_refs"] or [])

    # Build evaluation prompt
    parent_text = breadcrumb[-1] if breadcrumb else "General"
    eval_prompt = f"""You are quizzing a law student with ADHD. Keep ALL responses under 100 words. Never write walls of text.

The question asked was: "{session['current_question']}"
The topic is: "{parent_text}"
Correct answer involves: "{node['text']}"
{f'Related subtopics (for your reference only, NOT required in the answer): {", ".join(children_texts)}' if children_texts else ''}
{case_context}
{rule_context}

The student answered: "{body.answer}"

GRADING RULES:
- Grade ONLY against what the question actually asked — not against the full topic tree
- If the student correctly answers the specific question, verdict is CORRECT even if they didn't mention subtopics
- PARTIAL means they got the right idea but with a meaningful error or confusion
- INCORRECT means they got the core concept wrong
- Do NOT mark PARTIAL just because they didn't list extra details the question didn't ask for

Evaluate:
1. What they got right (1 sentence)
2. What they could explore next (1-2 brief pointers, framed as "next time you could also mention..." NOT as things they got wrong)
3. Verdict

Be encouraging. No lectures.

Your FINAL line must be ONLY one of these three words, nothing else:
CORRECT
PARTIAL
INCORRECT"""

    async def stream_response():
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"

        full_response = ""
        input_tokens = 0
        output_tokens = 0

        try:
            # Step 1: Stream evaluation
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 300,
                        "messages": [{"role": "user", "content": eval_prompt}],
                        "stream": True,
                    },
                    timeout=60.0,
                ) as response:
                    if response.status_code != 200:
                        yield f"data: {json.dumps({'type': 'error', 'error': f'API error {response.status_code}'})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = event.get("type", "")
                        if event_type == "content_block_delta":
                            text = event.get("delta", {}).get("text", "")
                            if text:
                                full_response += text
                                yield f"data: {json.dumps({'type': 'feedback', 'text': text})}\n\n"
                        elif event_type == "message_start":
                            input_tokens = event.get("message", {}).get("usage", {}).get("input_tokens", 0)
                        elif event_type == "message_delta":
                            output_tokens = event.get("usage", {}).get("output_tokens", 0)

        except Exception as e:
            print(f"Session respond stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            return

        # Step 2: Determine verdict
        # Search from bottom up for the verdict keyword
        verdict = "INCORRECT"
        # Strip markdown formatting for matching
        clean = full_response.replace("*", "").replace("#", "").strip()
        print(f"[SESSION DEBUG] Full response last 200 chars: {clean[-200:]}")
        for line in reversed(clean.splitlines()):
            stripped = line.strip().upper()
            # Remove common prefixes like "3." or "Verdict:" or "**"
            stripped = re.sub(r'^[\d.\-\s*#]+', '', stripped).strip()
            stripped = re.sub(r'^VERDICT[:\s]*', '', stripped).strip()
            if stripped in ("CORRECT", "PARTIAL", "INCORRECT"):
                verdict = stripped
                break
        # Fallback: scan entire response if no clean line match
        if verdict == "INCORRECT":
            # Check if response contains positive signals but no INCORRECT
            upper = clean.upper()
            has_incorrect = "INCORRECT" in upper
            has_correct = "CORRECT" in upper
            has_partial = "PARTIAL" in upper
            if has_incorrect:
                verdict = "INCORRECT"
            elif has_partial:
                verdict = "PARTIAL"
            elif has_correct:
                verdict = "CORRECT"
        print(f"[SESSION DEBUG] Verdict resolved: {verdict}")

        # Step 3: Update node_progress and session
        try:
            async with db_pool.acquire() as conn:
                # Upsert node progress
                if verdict == "CORRECT":
                    await conn.execute("""
                        INSERT INTO node_progress (user_id, mindmap_id, node_id, correct_streak, total_attempts, total_correct, mastery, last_response_time_ms, last_response_length, last_reviewed_at)
                        VALUES ($1, $2, $3, 1, 1, 1, 'learning', $4, $5, NOW())
                        ON CONFLICT (user_id, mindmap_id, node_id) DO UPDATE SET
                            correct_streak = node_progress.correct_streak + 1,
                            total_attempts = node_progress.total_attempts + 1,
                            total_correct = node_progress.total_correct + 1,
                            mastery = CASE WHEN node_progress.correct_streak + 1 >= 3 THEN 'mastered' ELSE 'learning' END,
                            last_response_time_ms = $4,
                            last_response_length = $5,
                            last_reviewed_at = NOW()
                    """, user_id, mindmap_id, current_node_id, body.response_time_ms, len(body.answer))
                else:
                    await conn.execute("""
                        INSERT INTO node_progress (user_id, mindmap_id, node_id, correct_streak, total_attempts, total_correct, mastery, last_response_time_ms, last_response_length, last_reviewed_at)
                        VALUES ($1, $2, $3, 0, 1, 0, 'learning', $4, $5, NOW())
                        ON CONFLICT (user_id, mindmap_id, node_id) DO UPDATE SET
                            correct_streak = 0,
                            total_attempts = node_progress.total_attempts + 1,
                            mastery = 'learning',
                            last_response_time_ms = $4,
                            last_response_length = $5,
                            last_reviewed_at = NOW()
                    """, user_id, mindmap_id, current_node_id, body.response_time_ms, len(body.answer))

                # Update session stats
                new_streak = session["streak"] + 1 if verdict == "CORRECT" else 0
                new_max_streak = max(session["max_streak"], new_streak)

                # Check if node just got mastered
                prog = await conn.fetchrow(
                    "SELECT mastery FROM node_progress WHERE user_id = $1 AND mindmap_id = $2 AND node_id = $3",
                    user_id, mindmap_id, current_node_id
                )
                just_mastered = prog and prog["mastery"] == "mastered"

                mastered_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM node_progress WHERE user_id = $1 AND mindmap_id = $2 AND mastery = 'mastered'",
                    user_id, mindmap_id
                )

                total_correct = session["total_correct"] + (1 if verdict == "CORRECT" else 0)
                total_incorrect = session["total_incorrect"] + (1 if verdict == "INCORRECT" else 0)

                # Step 4: Drift detection
                recent = await conn.fetch("""
                    SELECT last_response_time_ms, last_response_length FROM node_progress
                    WHERE user_id = $1 AND mindmap_id = $2 AND last_reviewed_at IS NOT NULL
                    ORDER BY last_reviewed_at DESC LIMIT 5
                """, user_id, mindmap_id)

                mode = "quiz"
                if len(recent) >= 3:
                    avg_time = sum(r["last_response_time_ms"] or 0 for r in recent) / len(recent)
                    avg_length = sum(r["last_response_length"] or 0 for r in recent) / len(recent)

                    short_answers = sum(1 for r in recent[:2] if (r["last_response_length"] or 0) < 20)

                    if (body.response_time_ms > avg_time * 2 and avg_time > 0) or short_answers >= 2:
                        mode = random.choice(["story", "analogy", "hypo"])
                    elif new_streak >= 3:
                        mode = "go_deeper"

                # Step 5: Pick next node
                branch_node_id = session["branch_node_id"]
                quizzable = await get_quizzable_nodes(conn, mindmap_id, user_id, branch_node_id)
                unmastered = [n for n in quizzable if n["mastery"] != "mastered"]

                # Count total quizzable
                total_quizzable = len(quizzable)

                next_node = None
                next_question = None
                next_breadcrumb = []
                next_case_refs = []
                next_rule_refs = []
                session_complete = False

                if not unmastered:
                    session_complete = True
                    await conn.execute("""
                        UPDATE study_sessions SET session_state = 'completed', ended_at = NOW(),
                            streak = $2, max_streak = $3, nodes_mastered = $4,
                            total_correct = $5, total_incorrect = $6, last_activity_at = NOW()
                        WHERE id = $1
                    """, session_id, new_streak, new_max_streak, mastered_count, total_correct, total_incorrect)
                else:
                    # Stay on current node until mastered, then advance
                    current_still_unmastered = [n for n in unmastered if n["node_id"] == current_node_id]
                    if current_still_unmastered:
                        next_node = current_still_unmastered[0]
                    else:
                        # Current node is mastered — move to next unmastered
                        other = [n for n in unmastered if n["node_id"] != current_node_id]
                        next_node = other[0] if other else unmastered[0]

                    # Get context for next question
                    next_node_full, next_breadcrumb, next_children, _ = await get_node_context(conn, mindmap_id, next_node["node_id"])
                    next_case_context, next_rule_context = await get_case_and_rule_context(conn, next_node_full)

                    next_question = await generate_question_via_claude(
                        next_node["text"], next_breadcrumb, next_children, mode, next_case_context, next_rule_context
                    )

                    next_case_refs = json.loads(next_node_full["case_refs"]) if isinstance(next_node_full["case_refs"], str) else (next_node_full["case_refs"] or [])
                    next_rule_refs = json.loads(next_node_full["rule_refs"]) if isinstance(next_node_full["rule_refs"], str) else (next_node_full["rule_refs"] or [])

                    await conn.execute("""
                        UPDATE study_sessions SET current_node_id = $2, current_question = $3, mode = $4,
                            streak = $5, max_streak = $6, nodes_visited = nodes_visited + 1,
                            nodes_mastered = $7, total_correct = $8, total_incorrect = $9,
                            last_activity_at = NOW()
                        WHERE id = $1
                    """, session_id, next_node["node_id"], next_question, mode,
                        new_streak, new_max_streak, mastered_count, total_correct, total_incorrect)

                # Log usage
                cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
                try:
                    await log_api_usage("study_session_haiku", input_tokens, output_tokens, cost)
                except Exception:
                    pass

        except Exception as e:
            print(f"Session respond DB error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Failed to update progress'})}\n\n"
            return

        # Emit progress event
        yield f"data: {json.dumps({'type': 'progress', 'verdict': verdict, 'mastery': prog['mastery'] if prog else 'learning', 'streak': new_streak, 'max_streak': new_max_streak, 'mastered_count': mastered_count, 'total_nodes': total_quizzable, 'total_correct': total_correct, 'total_incorrect': total_incorrect})}\n\n"

        # Emit dopamine events
        if just_mastered:
            yield f"data: {json.dumps({'type': 'dopamine', 'event': 'mastered'})}\n\n"
        if new_streak in (5, 10, 25, 50):
            yield f"data: {json.dumps({'type': 'dopamine', 'event': f'streak_{new_streak}'})}\n\n"

        # Emit next question or completion
        if session_complete:
            yield f"data: {json.dumps({'type': 'complete', 'message': 'All nodes mastered! Great work!'})}\n\n"
        elif next_node and next_question:
            yield f"data: {json.dumps({'type': 'next_question', 'text': next_question, 'node_id': next_node['node_id'], 'node_text': next_node['text'], 'breadcrumb': next_breadcrumb, 'mode': mode, 'case_refs': next_case_refs, 'rule_refs': next_rule_refs})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/v1/study/session/{session_id}/skip")
async def session_skip(session_id: int, user: dict = Depends(require_auth)):
    """Skip current node and advance to next unmastered node"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    user_id = user["id"]

    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            "SELECT * FROM study_sessions WHERE id = $1 AND user_id = $2 AND session_state = 'active'",
            session_id, user_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Active session not found")

        mindmap_id = session["mindmap_id"]
        current_node_id = session["current_node_id"]

        quizzable = await get_quizzable_nodes(conn, mindmap_id, user_id, session["branch_node_id"])
        unmastered = [n for n in quizzable if n["mastery"] != "mastered" and n["node_id"] != current_node_id]

        if not unmastered:
            return {"completed": True, "message": "No more nodes to study!"}

        next_node = unmastered[0]
        node, breadcrumb, children_texts, _ = await get_node_context(conn, mindmap_id, next_node["node_id"])
        case_context, rule_context = await get_case_and_rule_context(conn, node)

        question = await generate_question_via_claude(
            next_node["text"], breadcrumb, children_texts, session["mode"] or "quiz", case_context, rule_context
        )

        await conn.execute("""
            UPDATE study_sessions SET current_node_id = $2, current_question = $3,
                streak = 0, nodes_visited = nodes_visited + 1, last_activity_at = NOW()
            WHERE id = $1
        """, session_id, next_node["node_id"], question)

        mastered_count = await conn.fetchval(
            "SELECT COUNT(*) FROM node_progress WHERE user_id = $1 AND mindmap_id = $2 AND mastery = 'mastered'",
            user_id, mindmap_id
        )

    return {
        "current_node_id": next_node["node_id"],
        "question": question,
        "breadcrumb": breadcrumb,
        "mode": session["mode"] or "quiz",
        "streak": 0,
        "nodes_mastered": mastered_count,
        "total_nodes": len(quizzable),
        "node_text": next_node["text"],
        "case_refs": json.loads(node["case_refs"]) if isinstance(node["case_refs"], str) else (node["case_refs"] or []),
        "rule_refs": json.loads(node["rule_refs"]) if isinstance(node["rule_refs"], str) else (node["rule_refs"] or []),
    }


@app.post("/api/v1/study/session/{session_id}/pause")
async def session_pause(session_id: int, user: dict = Depends(require_auth)):
    """Pause the current study session"""
    user_id = user["id"]
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE study_sessions SET session_state = 'paused', last_activity_at = NOW() WHERE id = $1 AND user_id = $2 AND session_state = 'active'",
            session_id, user_id
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Active session not found")
    return {"ok": True, "session_state": "paused"}


@app.get("/api/v1/study/session/progress/{mindmap_id}")
async def session_progress(mindmap_id: int, user: dict = Depends(require_auth)):
    """Get per-node mastery for the entire mindmap"""
    user_id = user["id"]
    async with db_pool.acquire() as conn:
        mm = await conn.fetchrow(
            "SELECT id FROM mindmaps WHERE id = $1 AND user_id = $2", mindmap_id, user_id
        )
        if not mm:
            raise HTTPException(status_code=404, detail="Mindmap not found")

        rows = await conn.fetch("""
            SELECT n.node_id, n.text, n.depth, n.is_leaf,
                   COALESCE(p.mastery, 'unseen') as mastery,
                   COALESCE(p.correct_streak, 0) as correct_streak,
                   COALESCE(p.total_attempts, 0) as total_attempts
            FROM mindmap_nodes n
            LEFT JOIN node_progress p ON p.mindmap_id = n.mindmap_id AND p.node_id = n.node_id AND p.user_id = $2
            WHERE n.mindmap_id = $1
            ORDER BY n.sort_order
        """, mindmap_id, user_id)

    return [
        {
            "node_id": r["node_id"],
            "text": r["text"],
            "depth": r["depth"],
            "is_leaf": r["is_leaf"],
            "mastery": r["mastery"],
            "correct_streak": r["correct_streak"],
            "total_attempts": r["total_attempts"],
        }
        for r in rows
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)