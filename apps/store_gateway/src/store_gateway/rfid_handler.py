import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from .storage import storage

logger = logging.getLogger(__name__)

rfid_router = APIRouter()

class RFIDEvent(BaseModel):
    event_type: str = Field(..., description="enter or exit")
    fitting_room_id: int
    sku_id: str
    timestamp: str
    metadata: Dict[str, Any] = {}

@rfid_router.post("/api/v1/rfid_event")
async def receive_rfid_event(event: RFIDEvent):
    """
    Webhook endpoint for RFID Readers (e.g. Sellmate).
    Saves event directly to encrypted SQLite.
    """
    try:
        # Convert timestamp to epoch ms if possible, otherwise use current
        try:
            dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
            ts_ms = int(dt.timestamp() * 1000)
        except ValueError:
            ts_ms = int(datetime.utcnow().timestamp() * 1000)
            
        storage.insert_rfid_event(
            event_type=event.event_type,
            fitting_room_id=event.fitting_room_id,
            sku_id=event.sku_id,
            timestamp_ms=ts_ms,
            metadata=event.metadata
        )
        logger.info(f"Recorded RFID {event.event_type} for room {event.fitting_room_id} (SKU: {event.sku_id})")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to process RFID webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
