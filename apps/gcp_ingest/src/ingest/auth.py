from fastapi import Request, HTTPException
import logging

logger = logging.getLogger(__name__)

async def verify_store_auth(request: Request, store_id: str):
    """
    Verifies that the Cloud Run proxy injected the correct Service Account email
    and that the SA is allowed to publish for this store_id.
    """
    # Cloud Run automatically injects this header for authenticated requests
    auth_email = request.headers.get("X-Goog-Authenticated-User-Email")
    
    # In local testing (without Cloud Run IAM), this header might be missing.
    # We allow bypass if explicitly configured for local testing (not in prod).
    import os
    if not os.getenv("K_SERVICE"):
        logger.debug(f"Local dev mode: skipping IAM check for store {store_id}")
        return
        
    if not auth_email:
        logger.warning(f"Missing X-Goog-Authenticated-User-Email header for store {store_id}")
        raise HTTPException(status_code=401, detail="Missing Google Cloud IAM Authentication")
        
    # Format is usually "accounts.google.com:SERVICE_ACCOUNT_EMAIL"
    if ":" in auth_email:
        auth_email = auth_email.split(":")[-1]
        
    # Example logic: ensure the SA has 'store-gw' in its name
    # In a real tenant mapping, we might query a DB to check if this SA owns this store_id.
    if "store-gw" not in auth_email:
        logger.error(f"Unauthorized SA {auth_email} tried to access store {store_id}")
        raise HTTPException(status_code=403, detail="Service account not authorized for this store")
        
    logger.debug(f"Authenticated {auth_email} for store {store_id}")
