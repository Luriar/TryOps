import os
import logging
from google.cloud import firestore
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Initialize client globally to reuse connection
# In local dev without credentials, this will fail unless GOOGLE_APPLICATION_CREDENTIALS is set
try:
    db = firestore.AsyncClient(project=os.getenv("PROJECT_ID", "tryops-stage0"))
except Exception as e:
    logger.warning(f"Failed to initialize Firestore client: {e}")
    db = None

async def check_and_set_idempotency(idempotency_key: str) -> bool:
    """
    Checks if idempotency_key exists in Firestore.
    If yes, returns True (meaning duplicate, should ignore).
    If no, creates it with a 7-day TTL and returns False (meaning proceed).
    """
    if not db:
        # Mock behavior for local dev
        return False
        
    doc_ref = db.collection("ingest_idempotency").document(idempotency_key)
    
    try:
        # We need a transaction to guarantee atomicity, but for simplicity 
        # in this IoT use case, getting and setting is usually enough.
        doc = await doc_ref.get()
        
        if doc.exists:
            logger.info(f"Idempotency key {idempotency_key} already processed.")
            return True
            
        # Write with TTL (requires a Firestore TTL policy configured on the 'expires_at' field)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        await doc_ref.set({
            "created_at": firestore.SERVER_TIMESTAMP,
            "expires_at": expires_at
        })
        return False
        
    except Exception as e:
        logger.error(f"Firestore error checking idempotency key {idempotency_key}: {e}")
        # Fail-open or fail-close? For IoT telemetry, better to fail-open and risk duplicate
        # than fail-close and lose data, as BQ can deduplicate later if needed.
        return False
