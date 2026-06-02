import sys
try:
    import pysqlcipher3
except ImportError:
    # Allow tests to run locally by mocking pysqlcipher3 with sqlite3
    import sqlite3
    import types
    mock_module = types.ModuleType('pysqlcipher3')
    mock_module.dbapi2 = sqlite3
    sys.modules['pysqlcipher3'] = mock_module

import pytest
import os
from contextlib import closing
from store_gateway.storage import Storage
import store_gateway.config as cfg

@pytest.fixture
def test_storage():
    db_path = "test_gateway.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Store Gateway uses Option C, so for standard tests we can use a key or rely on dev fallback
    store = Storage(db_path=db_path)
    yield store
    
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)

def test_storage_option_c_dev_fallback(monkeypatch):
    monkeypatch.setattr(cfg.config, "ENVIRONMENT", "dev")
    monkeypatch.setattr(cfg.config, "SQLCIPHER_KEY", "")
    monkeypatch.setattr(cfg.config, "DEV_FALLBACK_KEY", "fallback")
    
    store = Storage(db_path="test_option_c.db")
    assert store.key == "fallback"
    if os.path.exists("test_option_c.db"):
        os.remove("test_option_c.db")
    
def test_storage_option_c_prod_missing_key(monkeypatch):
    monkeypatch.setattr(cfg.config, "ENVIRONMENT", "production")
    monkeypatch.setattr(cfg.config, "SQLCIPHER_KEY", "")
    
    with pytest.raises(RuntimeError, match="CRITICAL: SQLCIPHER_KEY is missing"):
        Storage(db_path="test_option_c2.db")

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
