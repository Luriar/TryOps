import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from store_gateway.rfid_handler import rfid_router
from unittest.mock import patch

app = FastAPI()
app.include_router(rfid_router)
client = TestClient(app)

@patch("store_gateway.rfid_handler.storage")
def test_receive_rfid_event(mock_storage):
    payload = {
        "event_type": "enter",
        "fitting_room_id": 1,
        "sku_id": "SKU_123",
        "timestamp": "2023-10-01T12:00:00Z"
    }
    res = client.post("/api/v1/rfid_event", json=payload)
    assert res.status_code == 200
    mock_storage.insert_rfid_event.assert_called_once()
