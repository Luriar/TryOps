import pytest
from datetime import datetime
from stage0.csi_collector import CSICollector

def test_csi_collector_connection():
    collector = CSICollector()
    assert not collector.is_connected
    collector.connect()
    assert collector.is_connected
    collector.disconnect()
    assert not collector.is_connected

def test_generate_simulated_data():
    collector = CSICollector()
    base = datetime.now()
    
    # Test empty scenario (std ~ 0.5)
    df_empty = collector.generate_simulated_data(1, base, "empty")
    assert len(df_empty) == 60
    assert df_empty["rssi"].std() < 2.0
    
    # Test moving scenario (std ~ 6.0)
    df_moving = collector.generate_simulated_data(1, base, "moving")
    assert len(df_moving) == 60
    assert df_moving["rssi"].std() > 3.0
    
    # Test static scenario
    df_static = collector.generate_simulated_data(1, base, "static")
    assert len(df_static) == 60
    
    # Test noisy scenario
    df_noisy = collector.generate_simulated_data(1, base, "noisy")
    assert len(df_noisy) == 60
    
    # Test fallback
    df_other = collector.generate_simulated_data(1, base, "other")
    assert df_other["rssi"][0] == 0.0
