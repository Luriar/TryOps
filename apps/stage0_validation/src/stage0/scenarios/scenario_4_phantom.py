from stage0.csi_collector import CSICollector
from stage0.aggregator import DataAggregator
from stage0.signals import JointSignals
from datetime import datetime, timedelta
import polars as pl

def run_scenario():
    """
    Scenario 4: Phantom Detection
    """
    collector = CSICollector()
    agg = DataAggregator()
    
    base_time = datetime(2026, 5, 22, 13, 0, 0)
    base_ms = int(base_time.timestamp() * 1000)
    
    # Generate CSI: Occupied for 5 minutes
    raw_df = collector.generate_simulated_data(5, base_time, "moving")
    
    aggregated = []
    for i in range(5):
        w_start = base_time + timedelta(minutes=i)
        w_end = w_start + timedelta(minutes=1)
        agg_df = agg.aggregate_csi_minute(raw_df, w_start, w_end)
        if not agg_df.is_empty():
            aggregated.append(agg_df.row(0, named=True))
            
    csi_windows = pl.DataFrame(aggregated)
    
    # Missing RFID events
    rfid_events = []
    
    phantoms = JointSignals.detect_phantom(csi_windows, rfid_events)
    
    print("Scenario 4: Phantom Detection")
    print(f"Detected Phantoms: {len(phantoms)}")
    for p in phantoms:
        print(f"Phantom Alert! Time: {p['timestamp_ms']}, Confidence: {p['confidence']:.2f}")

if __name__ == "__main__":
    run_scenario()
