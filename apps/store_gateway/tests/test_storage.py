import pytest
import os
from contextlib import closing
from store_gateway.storage import Storage

@pytest.fixture
def test_storage():
    db_path = "test_gateway.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    store = Storage(db_path=db_path, key="test-key")
    yield store
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

def test_insert_raw_csi(test_storage):
    test_storage.insert_raw_csi("node_1", 1, 1000, -45, '{"data": [0.1]}')
    
    with closing(test_storage.get_connection()) as conn:
        cursor = conn.execute("SELECT * FROM raw_csi")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["node_id"] == "node_1"
        assert rows[0]["rssi"] == -45

def test_insert_rfid_event(test_storage):
    test_storage.insert_rfid_event("enter", 1, "SKU_123", 2000, {"color": "black"})
    
    with closing(test_storage.get_connection()) as conn:
        cursor = conn.execute("SELECT * FROM rfid_events")
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["sku_id"] == "SKU_123"

def test_insert_pos_event_idempotency(test_storage):
    test_storage.insert_pos_event("TXN_1", 3000, [{"sku": "SKU_123"}], "card")
    # Duplicate insert should not throw and not add a new row
    test_storage.insert_pos_event("TXN_1", 3000, [{"sku": "SKU_123"}], "card")
    
    with closing(test_storage.get_connection()) as conn:
        cursor = conn.execute("SELECT * FROM pos_events")
        rows = cursor.fetchall()
        assert len(rows) == 1

def test_pending_aggregates(test_storage):
    test_storage.insert_aggregates([
        {
            "fitting_room_id": 1,
            "window_start_ms": 1000,
            "window_end_ms": 2000,
            "activity_score": 0.5,
            "occupancy_estimate": 1,
            "movement_pattern": "moderate"
        }
    ])
    
    pending = test_storage.get_pending_aggregates()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"
    
    test_storage.mark_aggregates_sent([pending[0]["id"]])
    
    pending_after = test_storage.get_pending_aggregates()
    assert len(pending_after) == 0
