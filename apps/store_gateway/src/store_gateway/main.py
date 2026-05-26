import logging
import asyncio
import contextlib
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import config
from .storage import storage
from .mqtt_collector import MQTTCollector
from .rfid_handler import rfid_router
from .pos_poller import poll_pos_api
from .aggregator import run_aggregation
from .gcp_publisher import publish_to_gcp

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
mqtt_collector = MQTTCollector()
scheduler = AsyncIOScheduler()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI."""
    logger.info("Starting TryOps Store Gateway...")
    
    # 1. Start MQTT Collector (runs its own thread inside paho-mqtt)
    mqtt_collector.start()
    
    # 2. Schedule Tasks
    # POS Polling: Every 1 minute
    scheduler.add_job(poll_pos_api, 'interval', minutes=1, id="pos_poller")
    # Aggregation: Every 1 minute
    scheduler.add_job(run_aggregation, 'interval', minutes=1, id="aggregator")
    # GCP Publish: Every 5 minutes
    scheduler.add_job(publish_to_gcp, 'interval', minutes=5, id="gcp_publisher")
    # Cleanup old data: Every day at 3 AM
    scheduler.add_job(storage.delete_old_data, 'cron', hour=3, id="cleanup_job")
    
    scheduler.start()
    
    yield
    
    logger.info("Shutting down TryOps Store Gateway...")
    mqtt_collector.stop()
    scheduler.shutdown()


# Initialize FastAPI with Lifespan
app = FastAPI(title="TryOps Store Gateway", lifespan=lifespan)

# Include RFID Webhook Router
app.include_router(rfid_router)

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "store_id": config.STORE_ID}

def main():
    """Entry point for running with uvicorn programmatically if needed."""
    import uvicorn
    uvicorn.run("store_gateway.main:app", host=config.HTTP_HOST, port=config.HTTP_PORT, reload=False)

if __name__ == "__main__":
    main()
