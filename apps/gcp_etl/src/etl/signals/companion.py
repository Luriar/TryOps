import polars as pl

def calculate_companion_score(session_summary: pl.DataFrame) -> pl.DataFrame:
    """
    Companion Effect (동행인 효과 지수) 계산
    - max_occupancy가 2 이상이면 동행인이 룸 근처 혹은 안에 있음 (1.0)
    - unique_skus가 많고 duration이 길면 동행인이 옷을 계속 갖다주는 패턴(0.7)
    """
    if session_summary.is_empty():
        return pl.DataFrame()
        
    return session_summary.with_columns(
        pl.when(pl.col("max_occupancy") >= 2)
        .then(0.9)  # 물리적 다수 인원 감지
        .when((pl.col("unique_skus") >= 4) & (pl.col("duration_seconds") > 400))
        .then(0.7)  # 많은 옷 + 긴 시간 = 동행인이 가져다 줄 확률 높음
        .otherwise(0.1)
        .alias("companion_score")
    )
