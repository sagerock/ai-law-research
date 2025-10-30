"""
CourtListener Webhook Handler

This module receives and processes webhook events from CourtListener
to keep the database updated with new cases in real-time.
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncpg
import os

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# IP addresses that CourtListener webhooks come from
COURTLISTENER_IPS = ["34.210.230.218", "54.189.59.91"]

class SearchAlertPayload(BaseModel):
    alert: Dict[str, Any]
    results: List[Dict[str, Any]]

class WebhookMetadata(BaseModel):
    version: int
    event_type: str

class SearchAlertWebhook(BaseModel):
    payload: SearchAlertPayload
    webhook: WebhookMetadata

@router.post("/courtlistener/search-alert")
async def handle_search_alert(
    request: Request,
    webhook: SearchAlertWebhook,
    background_tasks: BackgroundTasks
):
    """
    Handle Search Alert webhook events from CourtListener.

    These events fire when new cases match your saved searches.
    We automatically import them into our database.
    """

    # Verify the request came from CourtListener
    client_ip = request.client.host
    if client_ip not in COURTLISTENER_IPS:
        print(f"⚠️  Webhook from unknown IP: {client_ip}")
        # In production, you might want to reject this
        # raise HTTPException(status_code=403, detail="Unauthorized")

    # Get idempotency key to prevent duplicate processing
    idempotency_key = request.headers.get("Idempotency-Key")

    print(f"📬 Received Search Alert webhook: {webhook.payload.alert.get('name')}")
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
            date_filed = result.get("dateFiled")
            url = result.get("absolute_url", "")

            # Check if we already have this case
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM cases WHERE id = $1)",
                case_id
            )

            if exists:
                print(f"   ℹ️  Case {case_id} already exists, skipping")
                continue

            # Look up court
            court_db_id = None
            if court_id:
                court_db_id = await conn.fetchval(
                    "SELECT id FROM courts WHERE court_listener_id = $1",
                    court_id
                )

            # Insert new case
            await conn.execute("""
                INSERT INTO cases (
                    id, title, court_id, decision_date,
                    metadata, source_url, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (id) DO NOTHING
            """,
                case_id,
                case_name,
                court_db_id,
                date_filed,
                result,  # Store full result as metadata
                url
            )

            print(f"   ✅ Imported case: {case_name[:60]}")

            # TODO: Generate embeddings in another background task
            # TODO: Fetch full opinion text if available

    except Exception as e:
        print(f"   ❌ Error processing webhook: {e}")
    finally:
        await conn.close()

@router.post("/courtlistener/docket-alert")
async def handle_docket_alert(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Docket Alert webhook events.

    These fire when cases you're monitoring get new filings.
    """

    payload = await request.json()
    idempotency_key = request.headers.get("Idempotency-Key")

    print(f"📬 Received Docket Alert webhook")
    print(f"   New entries: {len(payload.get('payload', {}).get('results', []))}")

    # Process in background
    background_tasks.add_task(
        process_docket_updates,
        payload,
        idempotency_key
    )

    return {"status": "received", "idempotency_key": idempotency_key}

async def process_docket_updates(payload: Dict, idempotency_key: str):
    """Process docket update events"""

    # TODO: Update case records with new filings
    # TODO: Notify users who are following this case

    print(f"   Processing docket updates...")
    pass

@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint"""
    return {"status": "ok", "service": "webhook_handler"}
