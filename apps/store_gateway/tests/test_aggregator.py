import sys
try:
    import pysqlcipher3
except ImportError:
    import sqlite3
    import types
    mock_module = types.ModuleType('pysqlcipher3')
    mock_module.dbapi2 = sqlite3
    sys.modules['pysqlcipher3'] = mock_module

import pytest
from unittest.mock import patch, MagicMock
from store_gateway.aggregator import run_aggregation

@patch("store_gateway.aggregator.storage")
def test_run_aggregation_no_data(mock_storage):
    mock_conn = MagicMock()
    mock_storage.get_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = []
    
    run_aggregation(1)
    
    mock_storage.insert_aggregates.assert_not_called()

@patch("store_gateway.aggregator.storage")
def test_run_aggregation_with_data(mock_storage):
    mock_conn = MagicMock()
    mock_storage.get_connection.return_value.__enter__.return_value = mock_conn
    
    mock_conn.execute.return_value.fetchall.return_value = [
        {"fitting_room_id": 1, "timestamp_ms": 1000, "rssi": -40},
        {"fitting_room_id": 1, "timestamp_ms": 1100, "rssi": -30},
        {"fitting_room_id": 2, "timestamp_ms": 1000, "rssi": -50},
        {"fitting_room_id": 2, "timestamp_ms": 1100, "rssi": -51}
    ]
    
    run_aggregation(1)
    
    mock_storage.insert_aggregates.assert_called_once()
    args, kwargs = mock_storage.insert_aggregates.call_args
    records = args[0]
    assert len(records) == 2
    
    # room 2 should be idle (std ~ 0.7)
    # room 1 should be active/moderate (std ~ 7)
    room_1 = next(r for r in records if r["fitting_room_id"] == 1)
    room_2 = next(r for r in records if r["fitting_room_id"] == 2)
    
    assert room_2["movement_pattern"] == "idle"
