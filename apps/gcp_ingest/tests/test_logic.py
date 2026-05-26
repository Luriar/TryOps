import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from ingest.pubsub_client import publish_messages
from ingest.auth import verify_store_auth
from fastapi import Request, HTTPException

@pytest.mark.asyncio
@patch('ingest.pubsub_client.publisher')
async def test_publish_messages_split(mock_publisher):
    # Setup mock
    mock_future = MagicMock()
    mock_publisher.publish.return_value = mock_future
    
    aggregates = [
        {"fitting_room_id": 1, "activity_score": 0.5},
        {"fitting_room_id": 2, "activity_score": 0.9}
    ]
    
    await publish_messages("store_001", "2023-01-01", aggregates)
    
    # Assert publisher was called exactly twice (once per array item)
    assert mock_publisher.publish.call_count == 2
    mock_future.result.assert_called()

@pytest.mark.asyncio
async def test_verify_store_auth_missing_header():
    request = MagicMock(spec=Request)
    request.headers = {}
    
    with patch('os.getenv', return_value="true"):
        with pytest.raises(HTTPException) as exc_info:
            await verify_store_auth(request, "store_001")
        assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_verify_store_auth_wrong_sa():
    request = MagicMock(spec=Request)
    request.headers = {"X-Goog-Authenticated-User-Email": "accounts.google.com:bad-hacker@gmail.com"}
    
    with patch('os.getenv', return_value="true"):
        with pytest.raises(HTTPException) as exc_info:
            await verify_store_auth(request, "store_001")
        assert exc_info.value.status_code == 403
