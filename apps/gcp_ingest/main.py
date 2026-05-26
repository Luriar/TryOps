# TryOps GCP Ingest API (FastAPI)
from fastapi import FastAPI, HTTPException, Security
from pydantic import BaseModel

app = FastAPI(title="TryOps GCP Ingest Service")

class IngestPayload(BaseModel):
    store_id: str
    timestamp: int
    csi_summary: list
    rfid_tags: list

@app.post("/ingest")
async def ingest_data(payload: IngestPayload):
    # TODO: Authenticate gateway and publish to GCP Pub/Sub topic
    print(f"Received data from store {payload.store_id}")
    return {"status": "success", "message": "Data published to Pub/Sub"}
