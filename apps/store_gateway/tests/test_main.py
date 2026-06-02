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
from fastapi.testclient import TestClient
from store_gateway.main import app, main
from unittest.mock import patch

def test_health_check():
    # TestClient invokes lifespan on enter
    with patch("store_gateway.main.mqtt_collector"):
        with patch("store_gateway.main.scheduler"):
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200
                assert response.json()["status"] == "healthy"

@patch("store_gateway.main.uvicorn.run")
def test_main(mock_run):
    main()
    mock_run.assert_called_once()
