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
from store_gateway.mqtt_collector import MQTTCollector
import json

def test_mqtt_collector_on_message():
    collector = MQTTCollector()
    
    with patch("store_gateway.mqtt_collector.storage") as mock_storage:
        msg = MagicMock()
        payload = {
            "node_id": "node1",
            "fitting_room_id": 1,
            "timestamp_ms": 1234,
            "rssi": -45,
            "csi_data": []
        }
        msg.payload = json.dumps(payload).encode('utf-8')
        
        collector.on_message(None, None, msg)
        mock_storage.insert_raw_csi.assert_called_once()
