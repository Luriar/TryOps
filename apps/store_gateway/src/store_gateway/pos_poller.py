import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta

from .config import config
from .storage import storage

logger = logging.getLogger(__name__)

async def poll_pos_api():
    """
    Polls the store POS API every minute for new transactions.
    Saves to SQLite encrypted buffer.
    Called by APScheduler.
    """
    # Look back 5 minutes to ensure no missed transactions
    since_dt = datetime.utcnow() - timedelta(minutes=5)
    since_str = since_dt.isoformat()
    
    url = f"{config.POS_API_URL}?since={since_str}"
    
    logger.info(f"Polling POS API: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    transactions = await response.json()
                    
                    count = 0
                    for txn in transactions:
                        txn_id = txn.get("transaction_id")
                        ts_str = txn.get("timestamp")
                        
                        try:
                            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            ts_ms = int(dt.timestamp() * 1000)
                        except (ValueError, TypeError):
                            ts_ms = int(datetime.utcnow().timestamp() * 1000)
                            
                        storage.insert_pos_event(
                            transaction_id=txn_id,
                            timestamp_ms=ts_ms,
                            items=txn.get("items", []),
                            payment_method=txn.get("payment_method", "unknown")
                        )
                        count += 1
                    if count > 0:
                        logger.info(f"Fetched {count} new POS transactions.")
                else:
                    logger.warning(f"POS API returned status {response.status}")
    except Exception as e:
        logger.error(f"POS Polling failed: {e}")
