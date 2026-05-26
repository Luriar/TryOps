import sys
import os
import polars as pl
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from etl.session_reconstruction import reconstruct_sessions

def test_session_reconstruction_empty():
    rfid_df = pl.DataFrame()
    csi_df = pl.DataFrame()
    
    res = reconstruct_sessions(rfid_df, csi_df)
    assert res.is_empty()

def test_session_reconstruction_basic():
    # 10:00:00 -> CSI Activity Starts
    # 10:01:00 -> RFID Detected
    # 10:05:00 -> CSI Activity Ends
    
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    
    csi_df = pl.DataFrame({
        "window_start": [base_time, base_time + timedelta(minutes=1), base_time + timedelta(minutes=2), base_time + timedelta(minutes=5)],
        "fitting_room_id": ["room_1", "room_1", "room_1", "room_1"],
        "activity_score": [0.8, 0.9, 0.5, 0.0],
        "occupancy_estimate": [1, 1, 1, 0]
    })
    
    rfid_df = pl.DataFrame({
        "timestamp": [base_time + timedelta(minutes=1, seconds=30)],
        "fitting_room_id": ["room_1"],
        "store_id": ["store_A"],
        "sku_id": ["SKU_XYZ"]
    })
    
    res = reconstruct_sessions(rfid_df, csi_df)
    
    # Check that a session was reconstructed
    assert not res.is_empty()
    assert res["unique_skus"][0] == 1
    assert res["store_id"][0] == "store_A"
