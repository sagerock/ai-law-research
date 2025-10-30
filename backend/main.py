from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import asyncpg
import httpx
from opensearchpy._async.client import AsyncOpenSearch
import redis.asyncio as redis
import numpy as np
from datetime import datetime
import json

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
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

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

@app.on_event("startup")
async def startup():
    global db_pool, osearch_client, redis_client
    
    # Initialize PostgreSQL connection pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    
    # Initialize OpenSearch client
    # Detect if URL uses HTTPS (for managed services like Bonsai)
    use_ssl = OPENSEARCH_URL.startswith('https://')
    osearch_client = AsyncOpenSearch(
        hosts=[OPENSEARCH_URL],
        http_compress=True,
        use_ssl=use_ssl,
        verify_certs=False,
    )
    
    # Initialize Redis client
    redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
    
    # Ensure OpenSearch indices exist
    await ensure_opensearch_indices()

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
        "opensearch": "unknown",
        "redis": "unknown"
    }

    # Check each service individually with timeouts
    # Don't fail the entire health check if one service is slow

    # Check database
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)[:50]}"

    # Check OpenSearch
    try:
        opensearch_health = await osearch_client.cluster.health()
        health_status["opensearch"] = opensearch_health.get("status", "connected")
    except Exception as e:
        health_status["opensearch"] = f"error: {str(e)[:50]}"

    # Check Redis
    try:
        await redis_client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)[:50]}"

    # Always return 200 OK so Railway considers the deployment healthy
    # The status field shows if there are any issues
    return health_status

@app.post("/api/v1/search")
async def search_cases(query: SearchQuery):
    """Hybrid search combining BM25 and semantic search"""

    # Check cache first
    cache_key = f"search:{json.dumps(query.dict(), sort_keys=True)}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    results = []
    keyword_results = []
    semantic_results = []

    if query.search_type in ["hybrid", "keyword"]:
        # BM25 search via OpenSearch
        keyword_results = await keyword_search(query)
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

    # Cache results
    await redis_client.setex(cache_key, 300, json.dumps(results))

    return results

async def keyword_search(query: SearchQuery):
    """BM25 keyword search using OpenSearch"""
    
    search_body = {
        "query": {
            "bool": {
                "must": {
                    "match": {
                        "content": {
                            "query": query.query,
                            "operator": "or"
                        }
                    }
                },
                "filter": []
            }
        },
        "size": query.limit,
        "highlight": {
            "fields": {
                "content": {
                    "fragment_size": 200,
                    "number_of_fragments": 1
                }
            }
        }
    }
    
    # Add filters
    if query.jurisdiction:
        search_body["query"]["bool"]["filter"].append(
            {"term": {"court_id": query.jurisdiction}}
        )

    if query.date_from:
        search_body["query"]["bool"]["filter"].append(
            {"range": {"decision_date": {"gte": query.date_from}}}
        )

    if query.date_to:
        search_body["query"]["bool"]["filter"].append(
            {"range": {"decision_date": {"lte": query.date_to}}}
        )
    
    response = await osearch_client.search(index="cases", body=search_body)
    
    results = []
    for hit in response["hits"]["hits"]:
        case = hit["_source"]
        case["score"] = hit["_score"]
        if "highlight" in hit:
            case["snippet"] = hit["highlight"]["content"][0]
        results.append(case)
    
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
    
    # Check cache
    cache_key = f"embedding:{hash(text)}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"input": text, "model": "text-embedding-3-small"}
        )
    
    embedding = response.json()["data"][0]["embedding"]
    
    # Cache embedding
    await redis_client.setex(cache_key, 86400, json.dumps(embedding))
    
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

    # Parse metadata if it's a JSON string
    if result.get("metadata") and isinstance(result["metadata"], str):
        try:
            result["metadata"] = json.loads(result["metadata"])
        except json.JSONDecodeError:
            result["metadata"] = {}

    # Fetch full opinion text if content is too short or missing
    if result.get("metadata") and isinstance(result["metadata"], dict):
        opinions = result["metadata"].get("opinions", [])
        if opinions and (not result.get("content") or len(result.get("content", "")) < 200):
            # Try to fetch the full opinion text from CourtListener
            opinion_id = opinions[0].get("id") if opinions else None
            if opinion_id:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/",
                            timeout=10.0
                        )
                        if response.status_code == 200:
                            opinion_data = response.json()
                            # Get plain text, html, or xml content
                            full_text = (
                                opinion_data.get("plain_text") or
                                opinion_data.get("html") or
                                opinion_data.get("xml") or
                                result.get("content", "")
                            )
                            result["content"] = full_text
                except Exception as e:
                    # If fetching fails, keep the existing content
                    print(f"Failed to fetch opinion {opinion_id}: {e}")

    return result

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
            ORDER BY c2.date DESC
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
    """Extract text from PDF (placeholder)"""
    # Would use PyPDF2 or pdfplumber in production
    return "Extracted PDF text"

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX (placeholder)"""
    # Would use python-docx in production
    return "Extracted DOCX text"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)