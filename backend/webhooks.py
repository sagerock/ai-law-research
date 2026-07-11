"""
CourtListener Webhook Handler

This module receives and processes webhook events from CourtListener
to keep the database updated with new cases in real-time.
"""

from fastapi import APIRouter, Request, BackgroundTasks, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncpg
import httpx
import json
import os
from datetime import date
from webhook_security import require_webhook_secret

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class SearchAlertPayload(BaseModel):
    alert: Dict[str, Any]
    results: List[Dict[str, Any]]

class WebhookMetadata(BaseModel):
    version: int
    event_type: int
    date_created: Optional[str] = None
    deprecation_date: Optional[str] = None

class SearchAlertWebhook(BaseModel):
    payload: SearchAlertPayload
    webhook: WebhookMetadata

@router.post("/courtlistener/search-alert")
async def handle_search_alert(
    request: Request,
    webhook: SearchAlertWebhook,
    background_tasks: BackgroundTasks,
    webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """
    Handle Search Alert webhook events from CourtListener.

    These events fire when new cases match your saved searches.
    We automatically import them into our database.
    """

    require_webhook_secret(webhook_secret)

    # Get idempotency key to prevent duplicate processing
    idempotency_key = request.headers.get("Idempotency-Key")

    print(f"Received Search Alert webhook: {webhook.payload.alert.get('name')}")
    print(f"   New results: {len(webhook.payload.results)}")

    # Process the new cases in the background
    background_tasks.add_task(
        process_new_cases,
        webhook.payload.results,
        idempotency_key
    )

    # Return 200 immediately so CourtListener knows we received it
    return {
        "status": "received",
        "results_count": len(webhook.payload.results),
        "idempotency_key": idempotency_key
    }


def extract_text_from_opinion(opinion_data: dict) -> str:
    """Extract plain text from a CourtListener opinion response."""
    from bs4 import BeautifulSoup
    if opinion_data.get("plain_text") and len(opinion_data["plain_text"]) > 100:
        return opinion_data["plain_text"]
    for field in ["html_lawbox", "html_with_citations", "html", "html_columbia", "xml_harvard"]:
        html_content = opinion_data.get(field, "")
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            if len(text) > 100:
                return text
    return ""


async def fetch_opinion_text(cluster_id: str) -> str:
    """Fetch full opinion text from CourtListener for a cluster."""
    cl_token = os.getenv("COURTLISTENER_API_KEY", "")
    cl_headers = {"Authorization": f"Token {cl_token}"} if cl_token else {}

    try:
        async with httpx.AsyncClient() as client:
            # Get cluster to find sub-opinions
            resp = await client.get(
                f"https://www.courtlistener.com/api/rest/v4/clusters/{cluster_id}/",
                headers=cl_headers, timeout=30,
            )
            if resp.status_code != 200:
                return ""

            cluster = resp.json()
            best_text = ""

            for op_url in cluster.get("sub_opinions", []):
                op_id = op_url.rstrip("/").split("/")[-1]
                op_resp = await client.get(
                    f"https://www.courtlistener.com/api/rest/v4/opinions/{op_id}/",
                    headers=cl_headers, timeout=30,
                )
                if op_resp.status_code == 200:
                    text = extract_text_from_opinion(op_resp.json())
                    if len(text) > len(best_text):
                        best_text = text

            return best_text
    except Exception as e:
        print(f"   Error fetching opinion text for cluster {cluster_id}: {e}")
        return ""


async def process_new_cases(results: List[Dict], idempotency_key: str):
    """
    Process new cases from webhook event.

    This runs in the background so we return 200 quickly.
    """

    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        for result in results:
            # Extract case data
            case_id = str(result.get("cluster_id") or result.get("id"))
            case_name = result.get("caseName", "")
            court_id = result.get("court_id")
            date_filed_str = result.get("dateFiled")
            url = result.get("absolute_url", "")

            # Parse date
            date_filed = None
            if date_filed_str:
                try:
                    date_filed = date.fromisoformat(date_filed_str)
                except (ValueError, TypeError):
                    pass

            # Extract citation if available
            reporter_cite = None
            citations = result.get("citation", [])
            if isinstance(citations, list) and citations:
                reporter_cite = citations[0]
            elif isinstance(citations, str):
                reporter_cite = citations

            # Check if we already have this case
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM cases WHERE id = $1)",
                case_id
            )

            if exists:
                print(f"   Case {case_id} already exists, skipping")
                continue

            # Look up court
            court_db_id = None
            if court_id:
                court_db_id = await conn.fetchval(
                    "SELECT id FROM courts WHERE court_listener_id = $1",
                    court_id
                )

            # Fetch full opinion text
            opinion_text = await fetch_opinion_text(case_id)
            if opinion_text:
                print(f"   Fetched {len(opinion_text)} chars of opinion text")

            # Insert new case
            await conn.execute("""
                INSERT INTO cases (
                    id, title, court_id, decision_date, reporter_cite,
                    content, metadata, source_url, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                ON CONFLICT (id) DO NOTHING
            """,
                case_id,
                case_name,
                court_db_id,
                date_filed,
                reporter_cite,
                opinion_text if opinion_text else None,
                json.dumps(result),
                url if url.startswith("http") else f"https://www.courtlistener.com{url}" if url else None,
            )

            print(f"   Imported case: {case_name[:60]}")

    except Exception as e:
        print(f"   Error processing webhook: {e}")
    finally:
        await conn.close()

@router.post("/courtlistener/docket-alert")
async def handle_docket_alert(
    request: Request,
    background_tasks: BackgroundTasks,
    webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
):
    """Handle Docket Alert webhook events."""
    require_webhook_secret(webhook_secret)
    payload = await request.json()
    idempotency_key = request.headers.get("Idempotency-Key")
    print(f"Received Docket Alert webhook")
    return {"status": "received", "idempotency_key": idempotency_key}

@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint"""
    return {"status": "ok", "service": "webhook_handler"}
