import polars as pl
from datetime import datetime

class DataAggregator:
    """
    Aggregates raw CSI (RSSI) data into 1-minute windows.
    Based on docs/design_aws/data_pipeline.md Section 2.
    """

    def aggregate_csi_minute(self, raw_df: pl.DataFrame, window_start: datetime, window_end: datetime) -> pl.DataFrame:
        """
        Aggregate raw CSI data into a 1-minute window using Polars.

        Args:
            raw_df: DataFrame containing raw CSI data (timestamp_ms, fitting_room_id, rssi)
            window_start: Start of the 1-minute window
            window_end: End of the 1-minute window

        Returns:
            pl.DataFrame: Aggregated data with activity_score, occupancy_estimate, and movement_pattern
        """
        start_ms = int(window_start.timestamp() * 1000)
        end_ms = int(window_end.timestamp() * 1000)

        # Filter by time window
        filtered_df = raw_df.filter(
            (pl.col("timestamp_ms") >= start_ms) & 
            (pl.col("timestamp_ms") < end_ms)
        )

        if len(filtered_df) == 0:
            return pl.DataFrame(schema={
                "fitting_room_id": pl.Int64,
                "window_start_ms": pl.Int64,
                "window_end_ms": pl.Int64,
                "activity_score": pl.Float64,
                "occupancy_estimate": pl.Int32,
                "movement_pattern": pl.Utf8
            })

        # Polars Aggregation logic from data_pipeline.md
        agg_df = (
            filtered_df.group_by("fitting_room_id")
            .agg([
                # std() can be null if count < 2, fill with 0
                pl.col("rssi").std().fill_null(0.0).alias("rssi_std")
            ])
            .with_columns([
                # activity_score (0~1 normalized)
                (pl.col("rssi_std") / 10.0).clip(0.0, 1.0).alias("activity_score"),
                # occupancy_estimate (RSSI std > 5.0 indicates movement, threshold 0.1 score = std 1.0 for occupancy)
                # Note: concept_validation_spec.md says activity_score < 0.1 is empty. 
                # So std > 1.0 is occupied. Let's use > 1.0 for occupancy.
                pl.col("rssi_std").gt(1.0).cast(pl.Int32).alias("occupancy_estimate"),
                # movement_pattern classification
                pl.when(pl.col("rssi_std") < 2.0).then(pl.lit("idle"))
                  .when(pl.col("rssi_std") < 7.0).then(pl.lit("moderate"))
                  .otherwise(pl.lit("active")).alias("movement_pattern"),
                pl.lit(start_ms).alias("window_start_ms"),
                pl.lit(end_ms).alias("window_end_ms")
            ])
            .drop("rssi_std")
        )
        
        return agg_df
