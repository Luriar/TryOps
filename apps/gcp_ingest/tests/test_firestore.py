import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from ingest.firestore_client import check_and_set_idempotency
import ingest.firestore_client as fc

@pytest.mark.asyncio
async def test_idempotency_no_db():
    original_db = fc.db
    fc.db = None
    try:
        assert await check_and_set_idempotency("key123") == False
    finally:
        fc.db = original_db

@pytest.mark.asyncio
@patch("ingest.firestore_client.db")
async def test_idempotency_exists(mock_db):
    mock_doc_ref = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc_ref
    
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    
    assert await check_and_set_idempotency("key123") == True

@pytest.mark.asyncio
@patch("ingest.firestore_client.db")
async def test_idempotency_not_exists(mock_db):
    mock_doc_ref = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc_ref
    
    mock_doc = MagicMock()
    mock_doc.exists = False
    mock_doc_ref.get = AsyncMock(return_value=mock_doc)
    mock_doc_ref.set = AsyncMock()
    
    assert await check_and_set_idempotency("key123") == False
    mock_doc_ref.set.assert_called_once()

@pytest.mark.asyncio
@patch("ingest.firestore_client.db")
async def test_idempotency_exception(mock_db):
    mock_doc_ref = MagicMock()
    mock_db.collection.return_value.document.return_value = mock_doc_ref
    
    mock_doc_ref.get = AsyncMock(side_effect=Exception("DB Error"))
    
    # Should fail open
    assert await check_and_set_idempotency("key123") == False
