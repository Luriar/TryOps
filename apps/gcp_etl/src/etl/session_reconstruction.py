import polars as pl
from datetime import timedelta

def reconstruct_sessions(rfid_df: pl.DataFrame, csi_df: pl.DataFrame, threshold: float = 0.1) -> pl.DataFrame:
    """
    Try-on session 재구성 알고리즘 (joint_signals_spec.md 기반)
    1. CSI activity > 임계값(0.1)인 연속 구간 식별 (점유 구간)
    2. RFID 이벤트를 시간 기준으로 조인
    """
    if rfid_df.is_empty() or csi_df.is_empty():
        return pl.DataFrame()
        
    # 1. CSI 점유 구간 식별
    # activity_score가 threshold보다 큰 곳을 찾음
    csi_occupancy = csi_df.filter(pl.col("activity_score") > threshold).sort("window_start")
    
    if csi_occupancy.is_empty():
         return pl.DataFrame()
    
    # 2. RFID 이벤트와 결합 (Join Asof)
    # RFID 이벤트 시점 근처의 가장 가까운 CSI 윈도우를 찾아서 매핑
    rfid_sorted = rfid_df.sort("timestamp")
    
    sessions = rfid_sorted.join_asof(
        csi_occupancy,
        left_on="timestamp",
        right_on="window_start",
        by="fitting_room_id",
        strategy="backward", # RFID 이벤트 직전의 가장 최근 CSI 윈도우
        tolerance="2m" # 2분 이내
    )
    
    # 3. 같은 점유 구간 안에 있는 이벤트를 하나의 세션으로 Group
    # 실제로는 연속성 체크가 들어가야 하지만, PoC 수준의 간단한 ID 부여 로직
    sessions = sessions.with_columns(
        (pl.col("fitting_room_id").cast(pl.Utf8) + "_" + pl.col("window_start").cast(pl.Utf8)).alias("session_id")
    )
    
    # 4. 세션별 요약
    session_summary = sessions.group_by("session_id", "store_id", "fitting_room_id").agg([
        pl.col("timestamp").min().alias("session_start"),
        pl.col("timestamp").max().alias("session_end"),
        pl.col("sku_id").n_unique().alias("unique_skus"),
        pl.col("sku_id").count().alias("total_events"),
        pl.col("activity_score").mean().alias("avg_activity_score"),
        pl.col("occupancy_estimate").max().alias("max_occupancy")
    ]).with_columns(
        ((pl.col("session_end") - pl.col("session_start")).dt.total_seconds()).alias("duration_seconds")
    )
    
    return session_summary
