"""
CourtListener Webhook Handler

This module receives and processes webhook events from CourtListener
to keep the database updated with new cases in real-time.
"""

from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncpg
import hashlib
import json
import os
from datetime import date
from courtlistener_opinions import fetch_courtlistener_document
from webhook_security import require_courtlistener_source

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


def _case_values(result: Dict[str, Any]) -> dict:
    case_id = str(result.get("cluster_id") or result.get("id"))
    date_filed = None
    if result.get("dateFiled"):
        try:
            date_filed = date.fromisoformat(result["dateFiled"])
        except (ValueError, TypeError):
            pass
    citations = result.get("citation", [])
    reporter_cite = citations[0] if isinstance(citations, list) and citations else citations
    url = result.get("absolute_url", "")
    return {
        "id": case_id,
        "title": result.get("caseName", ""),
        "court_id": result.get("court_id"),
        "decision_date": date_filed,
        "reporter_cite": reporter_cite if isinstance(reporter_cite, str) else None,
        "metadata": json.dumps(result),
        "source_url": (
            url if url.startswith("http")
            else f"https://www.courtlistener.com{url}" if url else None
        ),
    }


async def persist_new_case_stubs(results: List[Dict]) -> None:
    """Durably record deliveries before acknowledging the webhook."""
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    try:
        for result in results:
            values = _case_values(result)
            court_db_id = None
            if values["court_id"]:
                court_db_id = await conn.fetchval(
                    "SELECT id FROM courts WHERE court_listener_id = $1",
                    values["court_id"],
                )
            await conn.execute(
                """INSERT INTO cases (
                       id, title, court_id, decision_date, reporter_cite,
                       metadata, source_url, created_at
                   )
                   VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                   ON CONFLICT (id) DO NOTHING""",
                values["id"], values["title"], court_db_id,
                values["decision_date"], values["reporter_cite"],
                values["metadata"], values["source_url"],
            )
    finally:
        await conn.close()

@router.post("/courtlistener/search-alert")
async def handle_search_alert(
    request: Request,
    webhook: SearchAlertWebhook,
    background_tasks: BackgroundTasks,
):
    """
    Handle Search Alert webhook events from CourtListener.

    These events fire when new cases match your saved searches.
    We automatically import them into our database.
    """

    require_courtlistener_source(
        request.headers.get("x-real-ip"),
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )

    # Get idempotency key to prevent duplicate processing
    idempotency_key = request.headers.get("Idempotency-Key")

    print(f"Received Search Alert webhook: {webhook.payload.alert.get('name')}")
    print(f"   New results: {len(webhook.payload.results)}")

    # A provider retry remains possible until every result is durably represented.
    await persist_new_case_stubs(webhook.payload.results)

    # Hydrate public opinion text after the durable, idempotent insert.
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


async def fetch_opinion_text(cluster_id: str) -> str:
    """Fetch every typed writing through the canonical CourtListener assembler."""
    try:
        document = await fetch_courtlistener_document(
            cluster_id, os.getenv("COURTLISTENER_API_KEY")
        )
        return document.text if document else ""
    except Exception as e:
        print(f"   Error fetching opinion text for cluster {cluster_id}: {e}")
        return ""


async def process_new_cases(results: List[Dict], idempotency_key: str):
    """
    Process new cases from webhook event.

    This runs in the background so we return 200 quickly.
    """

    database_url = os.getenv("DATABASE_URL")
    for result in results:
        try:
            values = _case_values(result)
            case_id = values["id"]

            # Check if we already have this case
            conn = await asyncpg.connect(database_url)
            try:
                existing_content = await conn.fetchval(
                    "SELECT content FROM cases WHERE id = $1",
                    case_id,
                )

                # Look up court while the short-lived DB connection is open.
                court_db_id = None
                if values["court_id"]:
                    court_db_id = await conn.fetchval(
                        "SELECT id FROM courts WHERE court_listener_id = $1",
                        values["court_id"],
                    )
            finally:
                await conn.close()

            if existing_content and len(existing_content) >= 200:
                print(f"   Case {case_id} already has opinion text, skipping")
                continue

            # Do not hold a database connection during remote API requests.
            opinion_text = await fetch_opinion_text(case_id)
            if opinion_text:
                print(f"   Fetched {len(opinion_text)} chars of opinion text")

            conn = await asyncpg.connect(database_url)
            try:
                await conn.execute("""
                    INSERT INTO cases (
                        id, title, court_id, decision_date, reporter_cite,
                        content, content_hash, metadata, source_url, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        metadata = EXCLUDED.metadata,
                        source_url = EXCLUDED.source_url,
                        updated_at = NOW()
                    WHERE (cases.content IS NULL OR length(cases.content) < 200)
                      AND EXCLUDED.content IS NOT NULL
                """,
                    case_id,
                    values["title"],
                    court_db_id,
                    values["decision_date"],
                    values["reporter_cite"],
                    opinion_text if opinion_text else None,
                    hashlib.sha256(opinion_text.encode("utf-8")).hexdigest() if opinion_text else None,
                    values["metadata"],
                    values["source_url"],
                )
            finally:
                await conn.close()

            print(f"   Imported case: {values['title'][:60]}")
        except Exception as e:
            print(f"   Error processing webhook case: {e}")

@router.post("/courtlistener/docket-alert")
async def handle_docket_alert(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Handle Docket Alert webhook events."""
    require_courtlistener_source(
        request.headers.get("x-real-ip"),
        request.headers.get("x-forwarded-for"),
        request.client.host if request.client else None,
    )
    payload = await request.json()
    idempotency_key = request.headers.get("Idempotency-Key")
    print(f"Received Docket Alert webhook")
    return {"status": "received", "idempotency_key": idempotency_key}

@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint"""
    return {"status": "ok", "service": "webhook_handler"}
