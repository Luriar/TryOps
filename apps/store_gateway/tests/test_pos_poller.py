import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from store_gateway.pos_poller import poll_pos_api

@pytest.mark.asyncio
@patch("store_gateway.pos_poller.aiohttp.ClientSession.get")
@patch("store_gateway.pos_poller.storage")
async def test_poll_pos_api(mock_storage, mock_get):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=[
        {"transaction_id": "t1", "timestamp": "2023-01-01T12:00:00Z", "items": [], "payment_method": "card"}
    ])
    
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_resp
    mock_get.return_value = mock_ctx
    
    await poll_pos_api()
    mock_storage.insert_pos_event.assert_called_once()
