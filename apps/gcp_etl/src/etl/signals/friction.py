import polars as pl

def calculate_friction_score(session_summary: pl.DataFrame) -> pl.DataFrame:
    """
    Fitting Friction (피팅 마찰 지수) 계산
    - duration_seconds가 긴데 avg_activity_score가 비정상적으로 높으면
      옷이 잘 안 들어가서 낑낑대거나 입고 벗기를 반복하는 마찰 상황으로 간주
    """
    if session_summary.is_empty():
        return pl.DataFrame()
        
    return session_summary.with_columns(
        pl.when((pl.col("duration_seconds") > 240) & (pl.col("avg_activity_score") > 0.85))
        .then(0.9)  # 긴 시간 동안 과도한 움직임 = 피팅 마찰 발생
        .when((pl.col("duration_seconds") > 180) & (pl.col("avg_activity_score") > 0.75))
        .then(0.6)
        .otherwise(0.1)
        .alias("friction_score")
    )
