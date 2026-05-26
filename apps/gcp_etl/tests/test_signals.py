import sys
import os
import polars as pl
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from etl.signals.hesitation import calculate_hesitation_score
from etl.signals.companion import calculate_companion_score
from etl.signals.friction import calculate_friction_score

def test_hesitation_score():
    df = pl.DataFrame({
        "session_id": ["s1", "s2", "s3"],
        "duration_seconds": [100, 200, 350],
        "avg_activity_score": [0.6, 0.4, 0.1],
        "unique_skus": [2, 1, 1]
    })
    
    res = calculate_hesitation_score(df)
    
    # s1: duration < 120 -> 0.0
    assert res.filter(pl.col("session_id") == "s1")["hesitation_score"][0] == 0.0
    # s2: duration > 180 & act < 0.5 -> 0.6
    assert res.filter(pl.col("session_id") == "s2")["hesitation_score"][0] == 0.6
    # s3: duration > 300 & act < 0.3 -> 0.9
    assert res.filter(pl.col("session_id") == "s3")["hesitation_score"][0] == 0.9

def test_companion_score():
    df = pl.DataFrame({
        "session_id": ["s1", "s2", "s3"],
        "max_occupancy": [1, 2, 1],
        "unique_skus": [2, 2, 5],
        "duration_seconds": [100, 200, 450]
    })
    
    res = calculate_companion_score(df)
    
    # s1: normal -> 0.1
    assert res.filter(pl.col("session_id") == "s1")["companion_score"][0] == 0.1
    # s2: occupancy >= 2 -> 0.9
    assert res.filter(pl.col("session_id") == "s2")["companion_score"][0] == 0.9
    # s3: skus >= 4 & duration > 400 -> 0.7
    assert res.filter(pl.col("session_id") == "s3")["companion_score"][0] == 0.7

def test_friction_score():
    df = pl.DataFrame({
        "session_id": ["s1", "s2", "s3"],
        "duration_seconds": [100, 200, 300],
        "avg_activity_score": [0.5, 0.8, 0.9]
    })
    
    res = calculate_friction_score(df)
    
    # s1: normal -> 0.1
    assert res.filter(pl.col("session_id") == "s1")["friction_score"][0] == 0.1
    # s2: duration > 180 & act > 0.75 -> 0.6
    assert res.filter(pl.col("session_id") == "s2")["friction_score"][0] == 0.6
    # s3: duration > 240 & act > 0.85 -> 0.9
    assert res.filter(pl.col("session_id") == "s3")["friction_score"][0] == 0.9
