from stage0.csi_collector import CSICollector
from stage0.aggregator import DataAggregator
from datetime import datetime, timedelta
import polars as pl

def run_scenario():
    """
    Scenario 1: Occupancy Detection
    10m empty -> 10m static -> 10m moving -> 10m empty
    """
    collector = CSICollector()
    agg = DataAggregator()
    
    base_time = datetime(2026, 5, 22, 10, 0, 0)
    
    # Generate 4 stages of data
    df1 = collector.generate_simulated_data(10, base_time, "empty")
    df2 = collector.generate_simulated_data(10, base_time + timedelta(minutes=10), "static")
    df3 = collector.generate_simulated_data(10, base_time + timedelta(minutes=20), "moving")
    df4 = collector.generate_simulated_data(10, base_time + timedelta(minutes=30), "empty")
    
    raw_df = pl.concat([df1, df2, df3, df4])
    
    # Aggregate into 1-minute windows
    results = []
    for i in range(40):
        w_start = base_time + timedelta(minutes=i)
        w_end = w_start + timedelta(minutes=1)
        agg_df = agg.aggregate_csi_minute(raw_df, w_start, w_end)
        if not agg_df.is_empty():
            results.append(agg_df.row(0, named=True))
            
    print("Scenario 1: Occupancy Detection")
    print(f"Total windows processed: {len(results)}")
    
    # Verification
    # First 10 mins: empty (activity_score < 0.1)
    empty_1 = all(r["activity_score"] < 0.1 for r in results[0:10])
    # Next 10 mins: static (activity_score ~ 0.1 - 0.2)
    static_1 = all(0.1 <= r["activity_score"] < 0.5 for r in results[10:20])
    # Next 10 mins: moving (activity_score > 0.5)
    moving_1 = all(r["activity_score"] > 0.5 for r in results[20:30])
    
    success = empty_1 and static_1 and moving_1
    print(f"Validation {'PASSED' if success else 'FAILED'}")

if __name__ == "__main__":
    run_scenario()
