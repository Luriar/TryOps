import pytest
import polars as pl
from stage0.signals import JointSignals, Session

def test_reconstruct_sessions():
    csi_windows = pl.DataFrame({
        "fitting_room_id": [1, 1, 1],
        "window_start_ms": [1000, 61000, 400000],
        "window_end_ms": [60000, 120000, 460000],
        "activity_score": [0.5, 0.6, 0.2] # all > 0.1
    })
    
    rfid_events = [
        {"fitting_room_id": 1, "timestamp_ms": 2000, "event_type": "enter", "metadata": {}},
    ]
    
    sessions = JointSignals.reconstruct_sessions(rfid_events, csi_windows, "store1")
    assert len(sessions) == 2
    
def test_hesitation_score():
    csi_window = pl.DataFrame({
        "window_start_ms": [1000],
        "window_end_ms": [61000],
        "activity_score": [0.8]
    })
    rfid_events = [
        {"event_type": "enter", "metadata": {"category": "Pants", "size": "M"}},
        {"event_type": "enter", "metadata": {"category": "Pants", "size": "L"}},
    ]
    session = Session("store1", 1, rfid_events, csi_window)
    
    score = JointSignals.calculate_hesitation_score(session)
    assert score > 0
    # norm_swaps = 1/5 = 0.2 -> 0.4 * 0.2 = 0.08
    # avg_activity = 0.8 -> 0.3 * 0.8 = 0.24
    # duration = 60 / 600 = 0.1 -> 0.3 * 0.1 = 0.03
    # Total = 0.35
    assert abs(score - 0.35) < 0.01

def test_detect_phantom():
    csi_windows = pl.DataFrame({
        "fitting_room_id": [1, 1],
        "window_start_ms": [1000, 61000],
        "window_end_ms": [60000, 120000],
        "activity_score": [0.5, 0.6]
    })
    rfid_events = [] # no RFID
    
    phantoms = JointSignals.detect_phantom(csi_windows, rfid_events, threshold=0.3)
    assert len(phantoms) == 1
    assert phantoms[0]["fitting_room_id"] == 1
    assert phantoms[0]["confidence"] == 0.6
