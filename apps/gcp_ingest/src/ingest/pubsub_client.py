import os
import json
import logging
from typing import List, Dict, Any
from google.cloud import pubsub_v1
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

project_id = os.getenv("PROJECT_ID", "tryops-stage0")
topic_id = os.getenv("PUBSUB_TOPIC_ID", "store-telemetry")

try:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
except Exception as e:
    logger.warning(f"Failed to initialize Pub/Sub client: {e}")
    publisher = None
    topic_path = None

class PubSubError(Exception):
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def publish_messages(store_id: str, batch_start: str, aggregates: List[Dict[str, Any]]):
    """
    Splits the aggregates array into individual Pub/Sub messages.
    This ensures 1:1 mapping with BigQuery rows via Direct Subscription.
    Retries using exponential backoff on failure.
    """
    if not publisher:
        logger.info(f"MOCK PUBLISH: 1 batch to {topic_id}")
        return

    futures = []
    
    for row in aggregates:
        # Decorate each row with store metadata
        message_data = {
            "store_id": store_id,
            "batch_start": batch_start,
            **row
        }
        
        data_str = json.dumps(message_data).encode("utf-8")
        
        # Publish asynchronously
        future = publisher.publish(topic_path, data_str)
        futures.append(future)
        
    try:
        # Wait for all publishes in this batch to complete
        for future in futures:
            # Result() blocks, but we are inside an async def. 
            # In production, use asyncio.wrap_future if high throughput is needed.
            # However, google-cloud-pubsub's background thread handles the batching automatically.
            future.result(timeout=10)
            
        logger.info(f"Published {len(aggregates)} messages for store {store_id}")
    except Exception as e:
        logger.error(f"Failed to publish messages: {e}")
        raise PubSubError("PubSub publish failed")
