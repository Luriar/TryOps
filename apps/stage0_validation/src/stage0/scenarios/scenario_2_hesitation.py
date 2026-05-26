from stage0.csi_collector import CSICollector
from stage0.aggregator import DataAggregator
from stage0.signals import JointSignals
from stage0.rfid_synthesizer import RFIDSynthesizer
from datetime import datetime, timedelta
import polars as pl

def run_scenario():
    """
    Scenario 2: Hesitation Pattern
    Pattern A: 1 try (conversion)
    Pattern B: multiple tries (hesitation)
    Pattern C: no try (empty)
    """
    collector = CSICollector()
    agg = DataAggregator()
    synth = RFIDSynthesizer("dummy", "dummy")
    
    base_time = datetime(2026, 5, 22, 11, 0, 0)
    base_ms = int(base_time.timestamp() * 1000)
    
    # Generate CSI
    df_a = collector.generate_simulated_data(3, base_time, "moving")
    df_b = collector.generate_simulated_data(5, base_time + timedelta(minutes=10), "moving")
    df_c = collector.generate_simulated_data(3, base_time + timedelta(minutes=20), "static")
    
    raw_df = pl.concat([df_a, df_b, df_c])
    
    # Generate RFID (Mock)
    rfid_events = []
    # Pattern A (1 try)
    rfid_events.append({"fitting_room_id": 1, "timestamp_ms": base_ms + 10000, "event_type": "enter", "metadata": {"category": "T-shirt", "size": "M"}})
    rfid_events.append({"fitting_room_id": 1, "timestamp_ms": base_ms + 100000, "event_type": "exit", "metadata": {}})
    
    # Pattern B (hesitation, multiple enters)
    b_start_ms = base_ms + 600000
    rfid_events.append({"fitting_room_id": 1, "timestamp_ms": b_start_ms + 10000, "event_type": "enter", "metadata": {"category": "Pants", "size": "M"}})
    rfid_events.append({"fitting_room_id": 1, "timestamp_ms": b_start_ms + 120000, "event_type": "enter", "metadata": {"category": "Pants", "size": "L"}})
    rfid_events.append({"fitting_room_id": 1, "timestamp_ms": b_start_ms + 240000, "event_type": "exit", "metadata": {}})

    # Aggregate
    aggregated = []
    for i in range(30):
        w_start = base_time + timedelta(minutes=i)
        w_end = w_start + timedelta(minutes=1)
        agg_df = agg.aggregate_csi_minute(raw_df, w_start, w_end)
        if not agg_df.is_empty():
            aggregated.append(agg_df.row(0, named=True))
            
    csi_windows = pl.DataFrame(aggregated)
    sessions = JointSignals.reconstruct_sessions(rfid_events, csi_windows, "store_sim")
    
    print("Scenario 2: Hesitation Pattern")
    for idx, s in enumerate(sessions):
        score = JointSignals.calculate_hesitation_score(s)
        print(f"Session {idx+1}: Score = {score:.2f}")

if __name__ == "__main__":
    run_scenario()
