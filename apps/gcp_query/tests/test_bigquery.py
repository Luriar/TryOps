import pytest
from unittest.mock import patch, MagicMock
from query.bigquery_client import execute_query
from google.cloud import bigquery

def test_execute_query_success(monkeypatch):
    monkeypatch.setattr("query.bigquery_client.settings.use_mock_data", False)
    mock_client = MagicMock()
    mock_query_job = MagicMock()
    # Mocking rows return
    mock_row = {"store_id": "store1", "fitting_count": 5}
    mock_query_job.result.return_value = [mock_row]
    mock_client.query.return_value = mock_query_job
    
    monkeypatch.setattr("query.bigquery_client.client", mock_client)
    
    res = execute_query("SELECT *", [])
    assert len(res) == 1
    assert res[0]["store_id"] == "store1"

def test_execute_query_exception(monkeypatch):
    monkeypatch.setattr("query.bigquery_client.settings.use_mock_data", False)
    mock_client = MagicMock()
    mock_client.query.side_effect = Exception("BQ Error")
    monkeypatch.setattr("query.bigquery_client.client", mock_client)
    
    with pytest.raises(Exception, match="BQ Error"):
        execute_query("SELECT *", [])
