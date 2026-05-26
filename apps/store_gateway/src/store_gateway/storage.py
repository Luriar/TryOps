import json
import logging
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import closing

try:
    # Production: Use pysqlcipher3
    from pysqlcipher3 import dbapi2 as sqlcipher
    USE_SQLCIPHER = True
except ImportError:
    # Development: Fallback to standard sqlite3
    sqlcipher = sqlite3
    USE_SQLCIPHER = False

from .config import config

logger = logging.getLogger(__name__)

class Storage:
    """
    Local buffer using SQLCipher for AES-256 encryption.
    Stores raw CSI, RFID events, POS events, and 1-minute aggregates.
    """
    
    def __init__(self, db_path: str = config.DB_PATH, key: str = config.SQLCIPHER_KEY):
        self.db_path = db_path
        self.key = key
        self._init_db()

    def get_connection(self):
        """Get an encrypted database connection."""
        conn = sqlcipher.connect(self.db_path)
        if USE_SQLCIPHER:
            # Enable AES-256 encryption via SQLCipher PRAGMA
            conn.execute(f"PRAGMA key = '{self.key}';")
            # Force cipher test
            conn.execute("SELECT count(*) FROM sqlite_master;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database schema if it doesn't exist."""
        with closing(self.get_connection()) as conn:
            with conn:
                # Raw CSI buffer
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS raw_csi (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node_id TEXT,
                        fitting_room_id INTEGER,
                        timestamp_ms INTEGER,
                        rssi INTEGER,
                        csi_blob TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_csi_ts ON raw_csi(timestamp_ms)")
                
                # RFID Events
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rfid_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT,
                        fitting_room_id INTEGER,
                        sku_id TEXT,
                        timestamp_ms INTEGER,
                        metadata TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_rfid_ts ON rfid_events(timestamp_ms)")

                # POS Events
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pos_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transaction_id TEXT UNIQUE,
                        timestamp_ms INTEGER,
                        items TEXT,
                        payment_method TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pos_ts ON pos_events(timestamp_ms)")

                # Aggregates (1-minute Polars output)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS csi_aggregates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fitting_room_id INTEGER,
                        window_start_ms INTEGER,
                        window_end_ms INTEGER,
                        activity_score REAL,
                        occupancy_estimate INTEGER,
                        movement_pattern TEXT,
                        status TEXT DEFAULT 'pending'  -- 'pending', 'sent'
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_status ON csi_aggregates(status)")
            conn.commit()

    def insert_raw_csi(self, node_id: str, fitting_room_id: int, timestamp_ms: int, rssi: int, csi_blob: str):
        with closing(self.get_connection()) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO raw_csi (node_id, fitting_room_id, timestamp_ms, rssi, csi_blob) VALUES (?, ?, ?, ?, ?)",
                    (node_id, fitting_room_id, timestamp_ms, rssi, csi_blob)
                )

    def insert_rfid_event(self, event_type: str, fitting_room_id: int, sku_id: str, timestamp_ms: int, metadata: Dict):
        with closing(self.get_connection()) as conn:
            with conn:
                conn.execute(
                    "INSERT INTO rfid_events (event_type, fitting_room_id, sku_id, timestamp_ms, metadata) VALUES (?, ?, ?, ?, ?)",
                    (event_type, fitting_room_id, sku_id, timestamp_ms, json.dumps(metadata))
                )

    def insert_pos_event(self, transaction_id: str, timestamp_ms: int, items: List[Dict], payment_method: str):
        with closing(self.get_connection()) as conn:
            try:
                with conn:
                    conn.execute(
                        "INSERT INTO pos_events (transaction_id, timestamp_ms, items, payment_method) VALUES (?, ?, ?, ?)",
                        (transaction_id, timestamp_ms, json.dumps(items), payment_method)
                    )
            except sqlcipher.IntegrityError:
                pass

    def insert_aggregates(self, rows: List[Dict[str, Any]]):
        """Insert aggregated Polars results."""
        with closing(self.get_connection()) as conn:
            with conn:
                conn.executemany(
                    """
                    INSERT INTO csi_aggregates 
                    (fitting_room_id, window_start_ms, window_end_ms, activity_score, occupancy_estimate, movement_pattern, status) 
                    VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    """,
                    [
                        (
                            r["fitting_room_id"], r["window_start_ms"], r["window_end_ms"],
                            r["activity_score"], r["occupancy_estimate"], r["movement_pattern"]
                        ) for r in rows
                    ]
                )

    def get_pending_aggregates(self) -> List[Dict[str, Any]]:
        """Fetch unsent aggregates for GCP publishing."""
        with closing(self.get_connection()) as conn:
            cursor = conn.execute("SELECT * FROM csi_aggregates WHERE status = 'pending'")
            return [dict(row) for row in cursor.fetchall()]

    def mark_aggregates_sent(self, ids: List[int]):
        """Mark aggregates as sent after successful GCP publish."""
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        with closing(self.get_connection()) as conn:
            with conn:
                conn.execute(f"UPDATE csi_aggregates SET status = 'sent' WHERE id IN ({placeholders})", ids)

    def delete_old_data(self, retention_days: int = 7):
        """Delete raw data older than retention_days (Cron)."""
        cutoff_ms = int((datetime.utcnow() - timedelta(days=retention_days)).timestamp() * 1000)
        with closing(self.get_connection()) as conn:
            with conn:
                conn.execute("DELETE FROM raw_csi WHERE timestamp_ms < ?", (cutoff_ms,))
                conn.execute("DELETE FROM csi_aggregates WHERE status = 'sent' AND window_end_ms < ?", (cutoff_ms,))

# Global storage instance
storage = Storage()
