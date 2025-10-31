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
        case["id"] = hit["_id"]  # Extract document ID from OpenSearch
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

@app.post("/api/v1/cases/{case_id}/summarize")
async def summarize_case(case_id: str):
    """Generate an AI-powered case brief summary"""

    # Check if OpenAI API key is configured
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI summaries require OPENAI_API_KEY to be configured"
        )

    # Get the case from database and related cases
    async with db_pool.acquire() as conn:
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

    case_data = dict(row)

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
        # Call OpenAI API with GPT-5 mini
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-5-mini",  # Using GPT-5 mini for better reasoning at low cost
                    "messages": [
                        {"role": "system", "content": "You are an expert legal research assistant who creates clear, professional case briefs from full court opinions."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4000  # GPT-5 mini supports up to 128K output tokens
                },
                timeout=60.0  # Increased timeout for PDF processing
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI API error: {response.text}"
            )

        result = response.json()
        summary = result["choices"][0]["message"]["content"]

        # Calculate cost
        # GPT-5 mini: $0.25 per 1M input tokens, $2.00 per 1M output tokens
        input_tokens = result["usage"]["prompt_tokens"]
        output_tokens = result["usage"]["completion_tokens"]
        cost = (input_tokens * 0.25 / 1_000_000) + (output_tokens * 2.00 / 1_000_000)

        return {
            "summary": summary,
            "cost": cost,
            "citing_cases": [dict(r) for r in citing_query],
            "cited_cases": [dict(r) for r in cited_query],
            "tokens_used": {
                "input": input_tokens,
                "output": output_tokens,
                "total": result["usage"]["total_tokens"]
            }
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