import logging
import asyncio
import aiohttp
import json
import hashlib
from datetime import datetime
from google.oauth2 import service_account
from google.auth.transport.requests import Request

from .config import config
from .storage import storage

logger = logging.getLogger(__name__)

def get_oidc_token(audience: str) -> str:
    """Fetch OIDC token for Cloud Run authentication using Service Account JSON."""
    if not config.GCP_SA_KEY_PATH:
        logger.warning("No GCP_SA_KEY_PATH provided, sending without auth (dev only).")
        return ""
        
    try:
        # ID token for Cloud Run requires the URL as audience
        credentials = service_account.IDTokenCredentials.from_service_account_file(
            config.GCP_SA_KEY_PATH, target_audience=audience
        )
        request = Request()
        credentials.refresh(request)
        return credentials.token
    except Exception as e:
        logger.error(f"Failed to generate GCP OIDC Token: {e}")
        return ""

async def publish_to_gcp():
    """
    Reads pending aggregates and pushes them to Cloud Run Ingest endpoint.
    Called by APScheduler every 5 minutes.
    """
    pending = storage.get_pending_aggregates()
    if not pending:
        logger.info("No pending aggregates to publish to GCP.")
        return

    logger.info(f"Publishing {len(pending)} aggregates to GCP...")
    
    token = get_oidc_token(audience=config.INGEST_URL)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    batch_start = datetime.utcnow().isoformat()
    # 멱등성 보장 (idempotency_key)
    hash_input = f"{config.STORE_ID}_{batch_start}_{len(pending)}".encode('utf-8')
    idempotency_key = hashlib.sha256(hash_input).hexdigest()

    payload = {
        "store_id": config.STORE_ID,
        "idempotency_key": idempotency_key,
        "batch_start": batch_start,
        "aggregates": pending
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(config.INGEST_URL, json=payload, headers=headers, timeout=15) as response:
                if response.status in (200, 201, 202, 204):
                    logger.info(f"Successfully published batch {idempotency_key} to GCP.")
                    # Mark as sent
                    ids_to_mark = [r["id"] for r in pending]
                    storage.mark_aggregates_sent(ids_to_mark)
                else:
                    err_text = await response.text()
                    logger.error(f"GCP Publish failed with status {response.status}: {err_text}")
    except Exception as e:
        logger.error(f"GCP Publish network error: {e}")
