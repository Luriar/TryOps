from stage0.csi_collector import CSICollector
from stage0.aggregator import DataAggregator
from datetime import datetime, timedelta
import polars as pl

def run_scenario():
    """
    Scenario 5: Noise Robustness
    """
    collector = CSICollector()
    agg = DataAggregator()
    
    base_time = datetime(2026, 5, 22, 14, 0, 0)
    
    # Generate noisy CSI
    raw_df = collector.generate_simulated_data(10, base_time, "noisy")
    
    aggregated = []
    for i in range(10):
        w_start = base_time + timedelta(minutes=i)
        w_end = w_start + timedelta(minutes=1)
        agg_df = agg.aggregate_csi_minute(raw_df, w_start, w_end)
        if not agg_df.is_empty():
            aggregated.append(agg_df.row(0, named=True))
            
    print("Scenario 5: Noise Robustness")
    for row in aggregated:
        print(f"Time: {row['window_start_ms']}, Activity Score: {row['activity_score']:.2f}, Occupancy: {row['occupancy_estimate']}")

if __name__ == "__main__":
    run_scenario()
