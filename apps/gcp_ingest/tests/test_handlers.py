import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from ingest.main import app
from ingest.auth import verify_store_auth
from ingest.handlers import AggregatePayload

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
@patch('ingest.handlers.verify_store_auth', new_callable=AsyncMock)
@patch('ingest.handlers.check_and_set_idempotency', new_callable=AsyncMock)
@patch('ingest.handlers.publish_messages', new_callable=AsyncMock)
async def test_ingest_telemetry_success(mock_publish, mock_idempotency, mock_auth):
    mock_idempotency.return_value = False # Not duplicate
    
    payload = {
        "store_id": "store_001",
        "idempotency_key": "some_hash_123",
        "batch_start": "2023-10-01T12:00:00Z",
        "aggregates": [
            {"fitting_room_id": 1, "activity_score": 0.8},
            {"fitting_room_id": 2, "activity_score": 0.1}
        ]
    }
    
    response = client.post("/ingest", json=payload)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Batch queued for publishing"
    
    # Verify auth was checked
    mock_auth.assert_called_once()
    mock_idempotency.assert_called_once_with("some_hash_123")

@pytest.mark.asyncio
@patch('ingest.handlers.verify_store_auth', new_callable=AsyncMock)
@patch('ingest.handlers.check_and_set_idempotency', new_callable=AsyncMock)
async def test_ingest_telemetry_duplicate(mock_idempotency, mock_auth):
    mock_idempotency.return_value = True # Is duplicate
    
    payload = {
        "store_id": "store_001",
        "idempotency_key": "some_hash_123",
        "batch_start": "2023-10-01T12:00:00Z",
        "aggregates": []
    }
    
    response = client.post("/ingest", json=payload)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Already processed"
