import os
import logging
from fastapi import FastAPI
import google.cloud.logging
from .handlers import router

# Setup GCP Structured Logging if running in Cloud Run
if os.getenv("K_SERVICE"):
    client = google.cloud.logging.Client()
    client.setup_logging()
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("ingest")

app = FastAPI(title="TryOps Ingest Service")

# Include the POST /ingest route
app.include_router(router)

@app.get("/health")
def health_check():
    """Cloud Run health check endpoint."""
    return {"status": "healthy"}
