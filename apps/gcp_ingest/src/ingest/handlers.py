import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .auth import verify_store_auth
from .firestore_client import check_and_set_idempotency
from .pubsub_client import publish_messages

logger = logging.getLogger(__name__)

router = APIRouter()

class AggregatePayload(BaseModel):
    store_id: str
    idempotency_key: str
    batch_start: str
    aggregates: List[Dict[str, Any]]

@router.post("/ingest")
async def ingest_telemetry(request: Request, payload: AggregatePayload, background_tasks: BackgroundTasks):
    """
    Receives batched telemetry from store gateways.
    1. Verifies IAM authorization
    2. Checks idempotency
    3. Splits and Publishes to Pub/Sub
    """
    
    # 1. Auth Check
    await verify_store_auth(request, payload.store_id)
    
    logger.info(
        f"Received ingest request",
        extra={"store_id": payload.store_id, "idempotency_key": payload.idempotency_key}
    )
    
    # 2. Idempotency Check
    is_duplicate = await check_and_set_idempotency(payload.idempotency_key)
    if is_duplicate:
        # Return 200 immediately to acknowledge duplicate to the gateway
        return {"status": "ok", "message": "Already processed"}
        
    # 3. Publish to Pub/Sub
    try:
        # Run in background to return quickly to the Edge device
        # Tenacity handles retries inside this call
        background_tasks.add_task(
            publish_messages,
            store_id=payload.store_id,
            batch_start=payload.batch_start,
            aggregates=payload.aggregates
        )
    except Exception as e:
        logger.error(f"Failed to queue publish task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {"status": "ok", "message": "Batch queued for publishing"}
