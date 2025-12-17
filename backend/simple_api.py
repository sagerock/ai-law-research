#!/usr/bin/env python3

"""
Simplified API server for the frontend
Works with the data we've already imported
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncpg
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import openai
import sys
import hashlib
import secrets
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.brief_analyzer import BriefAnalyzer, BriefAnalysis

load_dotenv()

app = FastAPI(title="Legal Research API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://legal_user:legal_pass@localhost:5432/legal_research")

class SearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"
    limit: int = 20

class SearchResponse(BaseModel):
    results: List[dict]
    count: int
    query: str
    search_type: str

@app.get("/")
async def root():
    return {"message": "Legal Research API", "status": "running"}

@app.post("/api/v1/search", response_model=SearchResponse)
async def search_cases(request: SearchRequest):
    """Search for cases using keyword or semantic search"""

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Simple keyword search for now
        if request.search_type == "keyword":
            # Search in case names and content
            query_sql = """
                SELECT
                    id, title, court_id, decision_date,
                    COALESCE((metadata->>'citation_count')::int, 0) as citation_count,
                    source_url, content,
                    metadata
                FROM cases
                WHERE
                    title ILIKE $1 OR
                    content ILIKE $1
                ORDER BY COALESCE((metadata->>'citation_count')::int, 0) DESC NULLS LAST
                LIMIT $2
            """

            search_pattern = f"%{request.query}%"
            rows = await conn.fetch(query_sql, search_pattern, request.limit)

        else:
            # For semantic and hybrid, just return all cases ordered by citations
            # (In production, this would use embeddings)
            query_sql = """
                SELECT
                    id, title, court_id, decision_date,
                    COALESCE((metadata->>'citation_count')::int, 0) as citation_count,
                    source_url, content,
                    metadata,
                    CASE
                        WHEN title ILIKE $1 THEN 0.9
                        WHEN content ILIKE $1 THEN 0.7
                        ELSE 0.5
                    END as similarity
                FROM cases
                WHERE title IS NOT NULL
                ORDER BY
                    CASE WHEN title ILIKE $1 THEN 0 ELSE 1 END,
                    COALESCE((metadata->>'citation_count')::int, 0) DESC NULLS LAST
                LIMIT $2
            """

            search_pattern = f"%{request.query}%"
            rows = await conn.fetch(query_sql, search_pattern, request.limit)

        # Format results
        results = []
        for row in rows:
            # Parse metadata if it exists
            metadata = {}
            if row['metadata']:
                try:
                    metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                except:
                    metadata = {}

            result = {
                "id": row["id"],
                "case_name": row["title"] or "Unknown Case",
                "court_id": row["court_id"],
                "court_name": metadata.get("court", row["court_id"]),
                "date_filed": row["decision_date"].isoformat() if row["decision_date"] else None,
                "citation_count": row["citation_count"] or 0,
                "url": row["source_url"],
                "content": row["content"][:500] if row["content"] else None,
                "snippet": row["content"][:200] if row["content"] else None,
                "citations": metadata.get("citations", []),
                "citator_badge": "green" if row["citation_count"] and row["citation_count"] > 10 else "yellow"
            }

            # Add similarity for semantic search
            if "similarity" in row:
                result["similarity"] = float(row["similarity"])

            results.append(result)

        return SearchResponse(
            results=results,
            count=len(results),
            query=request.query,
            search_type=request.search_type
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

@app.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str):
    """Get a specific case by ID"""

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        row = await conn.fetchrow(
            "SELECT * FROM cases WHERE id = $1",
            case_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Case not found")

        # Parse metadata
        metadata = {}
        if row['metadata']:
            try:
                metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
            except:
                metadata = {}

        return {
            "id": row["id"],
            "case_name": row["case_name"],
            "court_id": row["court_id"],
            "court_name": metadata.get("court"),
            "date_filed": row["date_filed"].isoformat() if row["date_filed"] else None,
            "citation_count": row["citation_count"],
            "url": row["url"],
            "content": row["content"],
            "metadata": metadata
        }

    finally:
        await conn.close()

@app.post("/api/v1/cases/{case_id}/summarize")
async def generate_case_summary(case_id: str):
    """Generate an AI summary for a specific case"""

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Get the case
        row = await conn.fetchrow(
            "SELECT * FROM cases WHERE id = $1",
            case_id
        )

        if not row:
            raise HTTPException(status_code=404, detail="Case not found")

        # Check if we have OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="AI summaries not configured")

        # Generate summary using GPT-5-mini
        from openai import OpenAI
        import re
        client = OpenAI(api_key=openai_api_key)

        # Strip HTML tags if present
        case_text = row["content"] if row["content"] else ""
        if '<' in case_text and '>' in case_text:
            # Remove HTML tags
            case_text = re.sub('<.*?>', '', case_text)
            # Clean up extra whitespace
            case_text = ' '.join(case_text.split())

        # Limit to 3000 chars for cost
        case_text = case_text[:3000]

        prompt = f"""Analyze this legal case and provide a structured brief:

Case: {row["case_name"]}
Court: {row["court_id"]}
Date: {row["date_filed"]}

Case Text:
{case_text}

Please provide:
1. **Facts**: Key facts of the case (2-3 sentences)
2. **Issue**: The legal question(s) presented
3. **Holding**: The court's decision
4. **Reasoning**: Why the court decided this way (2-3 sentences)
5. **Significance**: Why this case matters for legal practice

Format as a clear, professional legal brief."""

        print(f"Sending {len(prompt)} chars to GPT-5-mini")
        print(f"First 500 chars of prompt: {prompt[:500]}")

        try:
            # Using GPT-5-mini with proper configuration
            response = client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=1200,  # Increased to allow for both reasoning and output
                reasoning_effort="low"  # Use low reasoning for simple summaries
            )

            print(f"Response object: {response}")

            if response.choices and len(response.choices) > 0:
                summary = response.choices[0].message.content
                print(f"Received summary: {len(summary) if summary else 0} chars")
                if not summary:
                    summary = "Unable to generate summary - no content returned from AI"
            else:
                summary = "Unable to generate summary - no choices in response"
                print("No choices in API response")
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            summary = f"Error generating summary: {str(e)}"

        # Calculate cost
        input_tokens = len(prompt) / 4  # Rough estimate
        output_tokens = len(summary) / 4
        cost = (input_tokens * 2 / 1_000_000) + (output_tokens * 8 / 1_000_000)

        # For now, return empty citation lists until we properly map citations
        # TODO: Map citation strings to case IDs
        citing_cases = []
        cited_cases = []

        return {
            "summary": summary,
            "cost": round(cost, 6),
            "citing_cases": citing_cases,
            "cited_cases": cited_cases
        }

    except Exception as e:
        import traceback
        print(f"Error in generate_case_summary: {e}")
        print(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()

@app.get("/api/v1/stats")
async def get_stats():
    """Get database statistics"""

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        case_count = await conn.fetchval("SELECT COUNT(*) FROM cases")
        court_count = await conn.fetchval("SELECT COUNT(*) FROM courts")
        citation_count = await conn.fetchval("SELECT COUNT(*) FROM citations")

        return {
            "cases": case_count,
            "courts": court_count,
            "citations": citation_count,
            "last_updated": datetime.now().isoformat()
        }

    finally:
        await conn.close()

@app.post("/api/v1/briefcheck")
async def analyze_brief(
    file: UploadFile = File(...),
    use_ai: Optional[bool] = False
):
    """Analyze a legal brief for citations and arguments"""

    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type {file_ext} not supported")

    # Read file content
    content = await file.read()

    # Initialize analyzer
    analyzer = BriefAnalyzer(
        database_url=DATABASE_URL,
        openai_api_key=os.getenv("OPENAI_API_KEY") if use_ai else None
    )

    try:
        # Analyze the brief
        analysis = await analyzer.analyze_brief(
            file_content=content,
            filename=file.filename,
            use_ai=use_ai
        )

        # Convert to dict for JSON response
        return {
            "filename": file.filename,
            "total_citations": analysis.total_citations,
            "extracted_citations": [vars(c) for c in analysis.extracted_citations],
            "validated_citations": analysis.validated_citations,
            "missing_authorities": analysis.missing_authorities,
            "problematic_citations": analysis.problematic_citations,
            "suggested_cases": analysis.suggested_cases,
            "key_arguments": analysis.key_arguments,
            "ai_summary": analysis.ai_summary,
            "analysis_cost": analysis.analysis_cost,
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Webhook configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", secrets.token_urlsafe(32))
ALLOWED_IPS = ["34.210.230.218", "54.189.59.91"]  # CourtListener webhook IPs

# Store processed webhook events to prevent duplicates
processed_events = set()

@app.post("/webhooks/courtlistener/{webhook_type}/{random_token}")
async def handle_courtlistener_webhook(
    webhook_type: str,
    random_token: str,
    request: Request,
    idempotency_key: Optional[str] = Header(None)
):
    """Handle incoming webhooks from CourtListener"""

    # Security checks
    client_host = request.client.host if request.client else None

    # In production, verify IP address
    # if client_host not in ALLOWED_IPS:
    #     raise HTTPException(status_code=403, detail="Forbidden")

    # Check idempotency to prevent duplicate processing
    if idempotency_key and idempotency_key in processed_events:
        return {"status": "already_processed"}

    try:
        # Parse webhook payload
        body = await request.json()
        webhook_data = body.get("webhook", {})
        payload = body.get("payload", {})

        conn = await asyncpg.connect(DATABASE_URL)

        try:
            if webhook_type == "docket-alert":
                # Handle docket updates
                results = payload.get("results", [])
                for entry in results:
                    await process_docket_entry(conn, entry)

            elif webhook_type == "search-alert":
                # Handle search alert matches
                results = payload.get("results", [])
                alert = payload.get("alert", {})
                await process_search_results(conn, results, alert)

            # Mark event as processed
            if idempotency_key:
                processed_events.add(idempotency_key)
                # Clean up old events (keep only last 10000)
                if len(processed_events) > 10000:
                    processed_events.clear()

            return {"status": "success", "processed": len(results) if 'results' in locals() else 0}

        finally:
            await conn.close()

    except Exception as e:
        print(f"Webhook processing error: {e}")
        return {"status": "error", "message": str(e)}

async def process_docket_entry(conn, entry: dict):
    """Process a new docket entry from webhook"""
    # Extract case info
    docket_id = entry.get("docket")
    date_filed = entry.get("date_filed")
    description = entry.get("description", "")

    # Log the update (in production, you'd update the case or notify users)
    print(f"New docket entry for case {docket_id}: {description[:100]}")

    # You could update the case in the database here
    # await conn.execute(...)

async def process_search_results(conn, results: List[dict], alert: dict):
    """Process new search results from webhook"""
    alert_name = alert.get("name", "Unknown Alert")

    for result in results:
        case_name = result.get("caseName", "")
        case_id = str(result.get("id", ""))

        print(f"New match for alert '{alert_name}': {case_name}")

        # You could import these cases or notify users here

@app.get("/webhooks/info")
async def webhook_info():
    """Show webhook endpoint information"""
    base_url = "https://your-domain.com"  # Replace with your actual domain

    return {
        "webhook_endpoints": {
            "docket_alerts": f"{base_url}/webhooks/courtlistener/docket-alert/{secrets.token_urlsafe(16)}",
            "search_alerts": f"{base_url}/webhooks/courtlistener/search-alert/{secrets.token_urlsafe(16)}",
        },
        "allowed_ips": ALLOWED_IPS,
        "instructions": "Add these URLs to your CourtListener webhook configuration"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)