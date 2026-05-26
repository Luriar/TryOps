import time
import logging
import polars as pl
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .storage import storage

logger = logging.getLogger(__name__)

def run_aggregation(window_minutes: int = 1):
    """
    Reads raw_csi data for the past `window_minutes`,
    aggregates it into 1-minute Polars DataFrame,
    and inserts into csi_aggregates table.
    Called by APScheduler every minute.
    """
    now = datetime.utcnow()
    # Floor to nearest minute for clean windows
    window_end = now.replace(second=0, microsecond=0)
    window_start = window_end - timedelta(minutes=window_minutes)
    
    start_ms = int(window_start.timestamp() * 1000)
    end_ms = int(window_end.timestamp() * 1000)
    
    logger.info(f"Running aggregation for window {window_start} to {window_end}")
    
    # In SQLite, we can read directly via Polars
    # BUT, pysqlcipher3 might not be supported natively by Polars read_database if it doesn't recognize the uri scheme.
    # Therefore, we fetch using our storage connection and convert to Polars.
    
    with storage.get_connection() as conn:
        cursor = conn.execute(
            "SELECT fitting_room_id, timestamp_ms, rssi FROM raw_csi WHERE timestamp_ms >= ? AND timestamp_ms < ?",
            (start_ms, end_ms)
        )
        rows = cursor.fetchall()
        
    if not rows:
        logger.info("No raw CSI data in this window.")
        return
        
    # Convert to list of dicts for Polars
    data = [{"fitting_room_id": r["fitting_room_id"], "rssi": r["rssi"]} for r in rows]
    df = pl.DataFrame(data)
    
    # Polars Aggregation Logic
    agg = (
        df.group_by("fitting_room_id")
        .agg([
            # activity_score: standard deviation of RSSI / 10, normalized to 0-1
            (pl.col("rssi").std() / 10.0).clip(0, 1).alias("activity_score"),
            # occupancy_estimate: if stdev > 5, then 1 else 0
            (pl.col("rssi").std() > 5.0).cast(pl.Int32).alias("occupancy_estimate"),
            # movement_pattern
            pl.when(pl.col("rssi").std() < 2.0).then(pl.lit("idle"))
              .when(pl.col("rssi").std() < 7.0).then(pl.lit("moderate"))
              .otherwise(pl.lit("active")).alias("movement_pattern")
        ])
    )
    
    # Handle NaN values for standard deviation when there is only 1 sample
    agg = agg.with_columns(
        pl.col("activity_score").fill_null(0.0),
        pl.col("occupancy_estimate").fill_null(0),
        pl.col("movement_pattern").fill_null("idle")
    )
    
    # Prepare rows for insertion
    records = []
    for row in agg.iter_rows(named=True):
        records.append({
            "fitting_room_id": row["fitting_room_id"],
            "window_start_ms": start_ms,
            "window_end_ms": end_ms,
            "activity_score": row["activity_score"],
            "occupancy_estimate": row["occupancy_estimate"],
            "movement_pattern": row["movement_pattern"]
        })
        
    storage.insert_aggregates(records)
    logger.info(f"Aggregated {len(records)} fitting rooms.")

