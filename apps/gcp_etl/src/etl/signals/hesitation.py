import polars as pl

def calculate_hesitation_score(session_summary: pl.DataFrame) -> pl.DataFrame:
    """
    Hesitation Score (망설임 지수) 계산
    - duration_seconds > 180 (3분) 이면서 avg_activity_score가 낮을 때 망설임 발생
    - unique_skus가 적을수록 확신 부족으로 간주
    """
    if session_summary.is_empty():
        return pl.DataFrame()
        
    return session_summary.with_columns(
        pl.when(pl.col("duration_seconds") < 120)
        .then(0.0)
        .when((pl.col("duration_seconds") > 300) & (pl.col("avg_activity_score") < 0.3))
        .then(0.9)  # 5분 이상 + 활동 매우 적음 = High Hesitation
        .when((pl.col("duration_seconds") > 180) & (pl.col("avg_activity_score") < 0.5))
        .then(0.6)  # 3분 이상 = Medium Hesitation
        .otherwise(0.2)
        .alias("hesitation_score")
    )
