import pytest
from unittest.mock import patch, AsyncMock
from store_gateway.gcp_publisher import publish_to_gcp

@pytest.mark.asyncio
@patch('store_gateway.gcp_publisher.storage')
@patch('store_gateway.gcp_publisher.aiohttp.ClientSession.post')
@patch('store_gateway.gcp_publisher.get_oidc_token')
async def test_publish_to_gcp_success(mock_get_token, mock_post, mock_storage):
    # Setup mocks
    mock_get_token.return_value = "mock_jwt_token"
    mock_storage.get_pending_aggregates.return_value = [
        {"id": 1, "fitting_room_id": 1, "activity_score": 0.5}
    ]
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_post.return_value.__aenter__.return_value = mock_response

    # Execute
    await publish_to_gcp()

    # Assertions
    mock_storage.get_pending_aggregates.assert_called_once()
    mock_post.assert_called_once()
    mock_storage.mark_aggregates_sent.assert_called_once_with([1])

@pytest.mark.asyncio
@patch('store_gateway.gcp_publisher.storage')
@patch('store_gateway.gcp_publisher.aiohttp.ClientSession.post')
async def test_publish_to_gcp_no_data(mock_post, mock_storage):
    mock_storage.get_pending_aggregates.return_value = []
    
    await publish_to_gcp()
    
    mock_post.assert_not_called()
