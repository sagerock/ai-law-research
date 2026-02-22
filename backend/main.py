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
import json
from jose import jwt, JWTError
from uuid import UUID

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


class BookmarkCreate(BaseModel):
    case_id: str
    folder: Optional[str] = None
    notes: Optional[str] = None


# Comment models
class CommentCreate(BaseModel):
    content: str


class CommentUpdate(BaseModel):
    content: str


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    law_school: Optional[str] = None
    graduation_year: Optional[int] = None
    is_public: Optional[bool] = None


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
async def log_api_usage(usage_type: str, input_tokens: int, output_tokens: int, cost: float):
    """Log API usage for transparency dashboard tracking"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO api_usage_log (usage_date, usage_type, call_count, input_tokens, output_tokens, estimated_cost, updated_at)
                VALUES (CURRENT_DATE, $1, 1, $2, $3, $4, CURRENT_TIMESTAMP)
                ON CONFLICT (usage_date, usage_type) DO UPDATE SET
                    call_count = api_usage_log.call_count + 1,
                    input_tokens = api_usage_log.input_tokens + EXCLUDED.input_tokens,
                    output_tokens = api_usage_log.output_tokens + EXCLUDED.output_tokens,
                    estimated_cost = api_usage_log.estimated_cost + EXCLUDED.estimated_cost,
                    updated_at = CURRENT_TIMESTAMP
            """, usage_type, input_tokens, output_tokens, cost)
    except Exception as e:
        # Don't fail the main request if logging fails
        print(f"Warning: Failed to log API usage: {e}")


@app.on_event("startup")
async def startup():
    global db_pool, osearch_client, redis_client

    # Initialize PostgreSQL connection pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

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
            """SELECT * FROM cases WHERE id = $1""",
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
async def get_case_summary(case_id: str):
    """Get cached AI summary if it exists"""
    async with db_pool.acquire() as conn:
        cached = await conn.fetchrow(
            """
            SELECT summary, model, input_tokens, output_tokens, cost, created_at
            FROM ai_summaries
            WHERE case_id = $1
            """,
            case_id
        )

        if not cached:
            return {"summary": None, "cached": False}

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
            "model": cached["model"]
        }

@app.post("/api/v1/cases/{case_id}/summarize")
async def summarize_case(case_id: str, authorization: Optional[str] = Header(None)):
    """Generate an AI-powered case brief summary"""

    # Check if Anthropic API key is configured
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI summaries require ANTHROPIC_API_KEY to be configured"
        )

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
        try:
            async with httpx.AsyncClient() as client:
                # Get cluster details to find opinion IDs
                cluster_resp = await client.get(
                    f"https://www.courtlistener.com/api/rest/v4/clusters/{cluster_id}/",
                    headers={"Authorization": f"Token {os.getenv('COURTLISTENER_API_KEY', '')}"},
                    timeout=30.0,
                )
                if cluster_resp.status_code == 200:
                    cluster_data = cluster_resp.json()
                    # sub_opinions is a list of opinion URLs
                    opinion_urls = cluster_data.get("sub_opinions", [])

                    for opinion_url in opinion_urls:
                        # Extract opinion ID from URL
                        opinion_id = opinion_url.rstrip("/").split("/")[-1]
                        opinion_resp = await client.get(
                            f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/",
                            headers={"Authorization": f"Token {os.getenv('COURTLISTENER_API_KEY', '')}"},
                            timeout=30.0,
                        )
                        if opinion_resp.status_code == 200:
                            opinion_data = opinion_resp.json()
                            # Try plain_text first, then html_with_citations
                            text = opinion_data.get("plain_text") or ""
                            if not text:
                                html = opinion_data.get("html_with_citations") or opinion_data.get("html") or ""
                                if html:
                                    import re
                                    text = re.sub('<.*?>', '', html)
                                    text = ' '.join(text.split())

                            if len(text) > 500:
                                fetched_content = text
                                break  # Use the first substantial opinion
                else:
                    print(f"CourtListener cluster API returned {cluster_resp.status_code}")
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
        # Call Anthropic Messages API with Claude Sonnet 4.5
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-5-20250929",
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
        # Claude Sonnet 4.5: $3 per 1M input tokens, $15 per 1M output tokens
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

        # Save the summary to database for caching
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
                case_id, summary, "claude-sonnet-4-5-20250929", input_tokens, output_tokens, cost
            )

        print(f"💾 Saved summary for case {case_id} to database")

        # Log usage for transparency dashboard
        await log_api_usage("ai_summary", input_tokens, output_tokens, cost)

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
            "model": "claude-sonnet-4-5-20250929"
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
        "charity_url": config.get("charity_url", "")
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
                   COUNT(cc.id) as case_count
            FROM collections c
            LEFT JOIN collection_cases cc ON c.id = cc.collection_id
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
            SELECT cc.id as collection_case_id, cc.notes, cc.added_at,
                   c.id, c.title, c.decision_date, c.reporter_cite,
                   ct.name as court_name
            FROM collection_cases cc
            JOIN cases c ON cc.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cc.collection_id = $1
            ORDER BY cc.added_at DESC
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
                "added_at": c["added_at"].isoformat() if c["added_at"] else None
            }
            for c in cases
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
            row = await conn.fetchrow("""
                INSERT INTO collection_cases (collection_id, case_id, notes)
                VALUES ($1, $2, $3)
                ON CONFLICT (collection_id, case_id) DO UPDATE SET notes = $3
                RETURNING id, added_at
            """, coll_id, data.case_id, data.notes)
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
            SELECT cc.notes, cc.added_at,
                   c.id, c.title, c.decision_date, c.reporter_cite,
                   ct.name as court_name
            FROM collection_cases cc
            JOIN cases c ON cc.case_id = c.id
            LEFT JOIN courts ct ON c.court_id = ct.id
            WHERE cc.collection_id = $1
            ORDER BY cc.added_at DESC
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
                "notes": c["notes"]
            }
            for c in cases
        ],
        "case_count": len(cases)
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
    """Get all comments for a case with user info"""
    async with db_pool.acquire() as conn:
        # Verify case exists
        case = await conn.fetchrow("SELECT id FROM cases WHERE id = $1", case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Get comments with user profile info
        rows = await conn.fetch("""
            SELECT c.id, c.case_id, c.user_id, c.content, c.is_edited,
                   c.created_at, c.updated_at, c.author_name,
                   p.username, p.full_name, p.avatar_url
            FROM comments c
            LEFT JOIN profiles p ON c.user_id = p.id
            WHERE c.case_id = $1
            ORDER BY c.created_at ASC
        """, case_id)

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
                "user": {
                    "username": row["author_name"] or row["username"],
                    "display_name": row["author_name"] or row["full_name"],
                    "avatar_url": row["avatar_url"],
                    "profile_username": row["username"]  # For linking to profile
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
        "user": {
            "username": profile["username"] if profile else email_name,
            "display_name": profile["full_name"] if profile else email_name,
            "avatar_url": profile["avatar_url"] if profile else None
        }
    }


@app.delete("/api/v1/comments/{comment_id}")
async def delete_comment(comment_id: int, user: dict = Depends(require_auth)):
    """Delete own comment"""
    async with db_pool.acquire() as conn:
        # Verify comment exists and belongs to user
        comment = await conn.fetchrow("""
            SELECT id, user_id FROM comments WHERE id = $1
        """, comment_id)

        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")

        if comment["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only delete your own comments")

        # Delete comment
        await conn.execute("DELETE FROM comments WHERE id = $1", comment_id)

    return {"status": "deleted"}


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
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tier, messages_today, last_message_date, daily_limit, model_override FROM user_tiers WHERE user_id = $1",
            user["id"],
        )

    if not row:
        return {
            "tier": "free",
            "messages_today": 0,
            "daily_limit": 15,
            "messages_remaining": 15,
            "model": "claude-haiku-4-5-20251001",
        }

    tier = row["tier"]
    messages_today = row["messages_today"]
    if row["last_message_date"] != date.today():
        messages_today = 0

    custom_limit = row["daily_limit"]
    if custom_limit is not None:
        daily_limit = custom_limit
    elif tier == "pro":
        daily_limit = None
    else:
        daily_limit = 15

    messages_remaining = None if daily_limit is None else max(0, daily_limit - messages_today)
    default_model = "claude-sonnet-4-5-20250929" if tier == "pro" else "claude-haiku-4-5-20251001"
    model = row["model_override"] or default_model

    return {
        "tier": tier,
        "messages_today": messages_today,
        "daily_limit": daily_limit,
        "messages_remaining": messages_remaining,
        "model": model,
    }


# --- Chat SSE endpoint ---

@app.post("/api/v1/study/chat")
async def study_chat(msg: ChatMessage, user: dict = Depends(require_auth)):
    """Stream AI study assistant response via SSE"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    user_id = user["id"]

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

        # Compute effective limit
        if custom_limit is not None:
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

        # Select model
        default_model = "claude-sonnet-4-5-20250929" if tier == "pro" else "claude-haiku-4-5-20251001"
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
        full_response = ""
        input_tokens = 0
        output_tokens = 0

        try:
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

            await log_api_usage(usage_type, input_tokens, output_tokens, cost)
        except Exception as e:
            print(f"Failed to save chat result: {e}")

        # Final done event
        remaining = None
        if effective_limit is not None:
            remaining = max(0, effective_limit - (messages_today + 1))
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cost': round(cost, 6)}, 'tier': tier, 'messages_remaining': remaining})}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


# ============================================================================
# Case Ask AI
# ============================================================================

@app.post("/api/v1/cases/{case_id}/ask")
async def case_ask_ai(case_id: str, msg: CaseAskMessage, user: dict = Depends(require_auth)):
    """Stream AI response about a specific case via SSE"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    user_id = user["id"]

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

        # Compute effective limit (shared counter with study chat)
        if custom_limit is not None:
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

        # Select model
        default_model = "claude-sonnet-4-5-20250929" if tier == "pro" else "claude-haiku-4-5-20251001"
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
        full_response = ""
        input_tokens = 0
        output_tokens = 0

        try:
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

            await log_api_usage(usage_type, input_tokens, output_tokens, cost)
        except Exception as e:
            print(f"Failed to save case ask result: {e}")

        # Final done event
        remaining = None
        if effective_limit is not None:
            remaining = max(0, effective_limit - (messages_today + 1))
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id, 'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens, 'cost': round(cost, 6)}, 'tier': tier, 'messages_remaining': remaining})}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


# ============================================================================
# Admin Panel
# ============================================================================

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
    default_pro_model = "claude-sonnet-4-5-20250929"

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
        default_model = "claude-sonnet-4-5-20250929" if tier == "pro" else "claude-haiku-4-5-20251001"

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

@app.get("/api/v1/casebook-cases")
async def get_casebook_cases(subject: str = None):
    """Return all cases that have AI briefs, for client-side instant search."""
    async with db_pool.acquire() as conn:
        if subject:
            rows = await conn.fetch("""
                SELECT c.id, c.title, c.reporter_cite, c.decision_date,
                       ct.name as court_name,
                       c.metadata->>'subject' as subject
                FROM cases c
                JOIN ai_summaries s ON s.case_id = c.id
                LEFT JOIN courts ct ON c.court_id = ct.id
                WHERE c.metadata->>'subject' = $1
                ORDER BY c.title
            """, subject)
        else:
            rows = await conn.fetch("""
                SELECT c.id, c.title, c.reporter_cite, c.decision_date,
                       ct.name as court_name,
                       c.metadata->>'subject' as subject
                FROM cases c
                JOIN ai_summaries s ON s.case_id = c.id
                LEFT JOIN courts ct ON c.court_id = ct.id
                ORDER BY c.title
            """)

    return [
        {
            "id": r["id"],
            "title": r["title"],
            "reporter_cite": r["reporter_cite"],
            "decision_date": r["decision_date"].isoformat() if r["decision_date"] else None,
            "court_name": r["court_name"],
            "subject": r["subject"],
        }
        for r in rows
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)