import pytest
import polars as pl
from datetime import datetime, timedelta
from stage0.aggregator import DataAggregator

def test_aggregate_csi_minute():
    aggregator = DataAggregator()
    
    # Generate some raw CSI data in a 1-minute window
    start_time = datetime(2026, 5, 22, 15, 0, 0)
    end_time = start_time + timedelta(minutes=1)
    
    start_ms = int(start_time.timestamp() * 1000)
    
    raw_df = pl.DataFrame({
        "timestamp_ms": [start_ms + 10000, start_ms + 20000, start_ms + 30000],
        "fitting_room_id": [1, 1, 1],
        "rssi": [-45.0, -42.0, -39.0] # std is 3.0
    })
    
    result = aggregator.aggregate_csi_minute(raw_df, start_time, end_time)
    
    assert len(result) == 1
    row = result.row(0, named=True)
    assert row["fitting_room_id"] == 1
    assert row["occupancy_estimate"] == 1 # std > 1.0
    assert row["movement_pattern"] == "moderate" # std = 3.0 -> 2.0 <= std < 7.0
    assert row["activity_score"] == 0.3 # 3.0 / 10.0
