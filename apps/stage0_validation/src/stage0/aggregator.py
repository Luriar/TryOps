"""
1분 윈도우 집계기 — v2.

joint_signals_spec.md v2 섹션 1.3의 "점유 윈도우"를 생성한다.
- CSI: activity_score (활동 강도) — 대기구역/광역의 주 신호
- mmWave: presence / still_presence / multi_occupancy_probability — 피팅룸의 주 신호
- fuse_minute(): 두 소스를 융합해 v2 점유 윈도우 완성

프라이버시 바이 디자인: raw 신호는 이 집계를 거친 뒤 폐기한다 (1분 집계만 적재).
"""
import polars as pl
from datetime import datetime


class DataAggregator:
    """Raw CSI/mmWave 데이터를 1분(또는 지정) 윈도우로 집계."""

    # ---------- CSI ----------

    def aggregate_csi_minute(self, raw_df: pl.DataFrame, window_start: datetime, window_end: datetime) -> pl.DataFrame:
        """
        CSI(RSSI) 집계 → activity_score.
        v2 변경: occupancy_estimate(인원 수) 제거 — 어떤 상용 CSI도 인원 카운트 불가 (ADR-001).
                 대신 presence(모션 기반 점유 추정, 정지 인물 놓칠 수 있음)를 반환.
        """
        start_ms = int(window_start.timestamp() * 1000)
        end_ms = int(window_end.timestamp() * 1000)

        filtered = raw_df.filter(
            (pl.col("timestamp_ms") >= start_ms) & (pl.col("timestamp_ms") < end_ms)
        )
        if len(filtered) == 0:
            return pl.DataFrame(schema={
                "fitting_room_id": pl.Int64,
                "window_start_ms": pl.Int64,
                "window_end_ms": pl.Int64,
                "activity_score": pl.Float64,
                "presence": pl.Boolean,
                "movement_pattern": pl.Utf8,
            })

        return (
            filtered.group_by("fitting_room_id")
            .agg([pl.col("rssi").std().fill_null(0.0).alias("rssi_std")])
            .with_columns([
                (pl.col("rssi_std") / 10.0).clip(0.0, 1.0).alias("activity_score"),
                # CSI presence = 모션 기반 추정. 정지 인물은 False로 나올 수 있음 (알려진 한계)
                pl.col("rssi_std").gt(1.0).alias("presence"),
                pl.when(pl.col("rssi_std") < 2.0).then(pl.lit("idle"))
                  .when(pl.col("rssi_std") < 7.0).then(pl.lit("moderate"))
                  .otherwise(pl.lit("active")).alias("movement_pattern"),
                pl.lit(start_ms).alias("window_start_ms"),
                pl.lit(end_ms).alias("window_end_ms"),
            ])
            .drop("rssi_std")
        )

    # ---------- mmWave (v2 신규) ----------

    def aggregate_mmwave_minute(
        self,
        raw_df: pl.DataFrame,
        window_start: datetime,
        window_end: datetime,
        presence_ratio_threshold: float = 0.3,
    ) -> pl.DataFrame:
        """
        mmWave 집계 → presence / still_presence / multi_occupancy_probability.

        - presence: 윈도우 내 재실 초 비율 > threshold (순간 드롭 보정 = hold_time 효과)
        - still_presence: 재실인데 정지 상태가 지배적 (Assistance Need의 원신호)
        - multi_occupancy_probability: target_count >= 2 비율 (0~1).
          🔴 인원 수 절대값이 아님 — "다중 점유 가능성"으로만 사용 (spec v2 §1.3)
        """
        start_ms = int(window_start.timestamp() * 1000)
        end_ms = int(window_end.timestamp() * 1000)

        filtered = raw_df.filter(
            (pl.col("timestamp_ms") >= start_ms) & (pl.col("timestamp_ms") < end_ms)
        )
        if len(filtered) == 0:
            return pl.DataFrame(schema={
                "fitting_room_id": pl.Int64,
                "window_start_ms": pl.Int64,
                "window_end_ms": pl.Int64,
                "presence": pl.Boolean,
                "still_presence": pl.Boolean,
                "mm_activity_score": pl.Float64,
                "multi_occupancy_probability": pl.Float64,
            })

        return (
            filtered.group_by("fitting_room_id")
            .agg([
                pl.col("presence").cast(pl.Float64).mean().alias("presence_ratio"),
                pl.col("still").cast(pl.Float64).mean().alias("still_ratio"),
                (pl.col("moving_energy") / 100.0).mean().clip(0.0, 1.0).alias("mm_activity_score"),
                pl.col("target_count").ge(2).cast(pl.Float64).mean().alias("multi_occupancy_probability"),
            ])
            .with_columns([
                pl.col("presence_ratio").gt(presence_ratio_threshold).alias("presence"),
                (pl.col("presence_ratio").gt(presence_ratio_threshold) & pl.col("still_ratio").gt(0.5)).alias("still_presence"),
                pl.lit(start_ms).alias("window_start_ms"),
                pl.lit(end_ms).alias("window_end_ms"),
            ])
            .drop(["presence_ratio", "still_ratio"])
        )

    # ---------- 융합 (v2 신규) ----------

    def fuse_minute(self, csi_agg: pl.DataFrame, mmwave_agg: pl.DataFrame) -> pl.DataFrame:
        """
        v2 점유 윈도우 융합 (spec v2 §5 센서-신호 매핑):
        - presence: mmWave 우선 (정지 인물 포함), 없으면 CSI 폴백
        - activity_score: CSI 우선, 없으면 mmWave 에너지 폴백
        """
        has_csi = not csi_agg.is_empty()
        has_mm = not mmwave_agg.is_empty()

        if has_csi and has_mm:
            fused = csi_agg.join(
                mmwave_agg.select([
                    "fitting_room_id", "window_start_ms",
                    pl.col("presence").alias("mm_presence"),
                    "still_presence", "mm_activity_score", "multi_occupancy_probability",
                ]),
                on=["fitting_room_id", "window_start_ms"],
                how="full", coalesce=True,
            )
            return fused.with_columns([
                pl.col("mm_presence").fill_null(pl.col("presence")).fill_null(False).alias("presence"),
                pl.lit("mmwave").alias("presence_source"),
                pl.col("activity_score").fill_null(pl.col("mm_activity_score")).fill_null(0.0).alias("activity_score"),
                pl.lit("csi").alias("activity_source"),
                pl.col("still_presence").fill_null(False),
                pl.col("multi_occupancy_probability").fill_null(0.0),
            ]).drop(["mm_presence", "mm_activity_score"])

        if has_mm:
            return mmwave_agg.with_columns([
                pl.lit("mmwave").alias("presence_source"),
                pl.col("mm_activity_score").alias("activity_score"),
                pl.lit("mmwave").alias("activity_source"),
            ]).drop("mm_activity_score")

        if has_csi:
            return csi_agg.with_columns([
                pl.lit("csi").alias("presence_source"),
                pl.lit("csi").alias("activity_source"),
                pl.lit(False).alias("still_presence"),
                pl.lit(0.0).alias("multi_occupancy_probability"),
            ])

        return pl.DataFrame()
