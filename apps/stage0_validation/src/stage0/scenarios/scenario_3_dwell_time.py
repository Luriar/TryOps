from stage0.csi_collector import CSICollector
from stage0.aggregator import DataAggregator
from stage0.signals import JointSignals
from datetime import datetime, timedelta
import polars as pl

def run_scenario():
    """
    Scenario 3: Dwell Time
    Short 2m -> empty 2m -> long 8m -> empty 2m
    """
    collector = CSICollector()
    agg = DataAggregator()
    
    base_time = datetime(2026, 5, 22, 12, 0, 0)
    
    # Generate CSI
    df_1 = collector.generate_simulated_data(2, base_time, "moving")
    df_2 = collector.generate_simulated_data(2, base_time + timedelta(minutes=2), "empty")
    df_3 = collector.generate_simulated_data(8, base_time + timedelta(minutes=4), "moving")
    df_4 = collector.generate_simulated_data(2, base_time + timedelta(minutes=12), "empty")
    
    raw_df = pl.concat([df_1, df_2, df_3, df_4])
    
    aggregated = []
    for i in range(14):
        w_start = base_time + timedelta(minutes=i)
        w_end = w_start + timedelta(minutes=1)
        agg_df = agg.aggregate_csi_minute(raw_df, w_start, w_end)
        if not agg_df.is_empty():
            aggregated.append(agg_df.row(0, named=True))
            
    csi_windows = pl.DataFrame(aggregated)
    sessions = JointSignals.reconstruct_sessions([], csi_windows, "store_sim")
    
    print("Scenario 3: Dwell Time")
    for idx, s in enumerate(sessions):
        print(f"Session {idx+1}: Duration = {s.duration} seconds")

if __name__ == "__main__":
    run_scenario()
