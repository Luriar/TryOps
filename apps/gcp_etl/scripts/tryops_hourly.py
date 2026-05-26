#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime, timedelta
import logging
import duckdb
import polars as pl

# sys.path 설정 (로컬 환경 및 crontab 실행 시 경로 문제 방지)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from etl.bigquery_io import fetch_raw_events, load_to_mart
from etl.session_reconstruction import reconstruct_sessions
from etl.signals.hesitation import calculate_hesitation_score
from etl.signals.companion import calculate_companion_score
from etl.signals.friction import calculate_friction_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def run_hourly_etl(store_id: str, target_date: str):
    logger.info(f"Starting hourly ETL for {store_id} on {target_date}")
    
    # 1. BQ에서 데이터 로드 (실제로는 target_date 전체 혹은 특정 시간대 필터링)
    # 여기서는 PoC 목적상 하루치 데이터를 통째로 땡겨와서 시간별 세션을 계산한다고 가정
    data = fetch_raw_events(store_id, target_date)
    raw_df = data.get("raw", pl.DataFrame())
    
    if raw_df.is_empty():
        logger.info("No data found. Exiting.")
        return
        
    # JSON 파싱 등은 BigQuery 혹은 Polars에서 처리했다고 가정
    # Mocking separated data for PoC
    if "event_type" in raw_df.columns:
        rfid_df = raw_df.filter(pl.col("event_type") == "rfid")
        csi_df = raw_df.filter(pl.col("event_type") == "csi")
    else:
        logger.warning("Mocking dummy data because real data is missing columns")
        rfid_df = pl.DataFrame({
            "timestamp": [datetime.now() - timedelta(minutes=10)],
            "fitting_room_id": ["room_1"],
            "sku_id": ["SKU_123"]
        })
        csi_df = pl.DataFrame({
            "window_start": [datetime.now() - timedelta(minutes=11)],
            "fitting_room_id": ["room_1"],
            "activity_score": [0.8],
            "occupancy_estimate": [1]
        })

    # 2. 세션 재구성
    session_summary = reconstruct_sessions(rfid_df, csi_df)
    
    if session_summary.is_empty():
        logger.info("No valid sessions found. Exiting.")
        return
        
    # 3. Signals 계산
    session_with_hesitation = calculate_hesitation_score(session_summary)
    session_with_companion = calculate_companion_score(session_summary)
    session_with_friction = calculate_friction_score(session_summary)
    
    # 4. DuckDB를 사용한 최종 마트 데이터 결합 및 집계
    # DuckDB can seamlessly query Polars dataframes
    con = duckdb.connect()
    con.register("sh", session_with_hesitation)
    con.register("sc", session_with_companion)
    con.register("sf", session_with_friction)
    
    final_mart_df = con.execute("""
        SELECT 
            sh.session_id,
            sh.store_id,
            sh.fitting_room_id,
            sh.session_start,
            sh.session_end,
            sh.duration_seconds,
            sh.unique_skus,
            sh.hesitation_score,
            sc.companion_score,
            sf.friction_score,
            CURRENT_TIMESTAMP as etl_processed_at
        FROM sh
        JOIN sc ON sh.session_id = sc.session_id
        JOIN sf ON sh.session_id = sf.session_id
    """).pl()
    
    # 5. BQ 마트에 적재
    load_to_mart("mart_hourly_sessions", final_mart_df, target_date)
    logger.info("Hourly ETL completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TryOps Hourly ETL")
    parser.add_argument("--store_id", required=True, help="Store ID to process")
    parser.add_argument("--date", required=False, help="Target Date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    target_date = args.date if args.date else datetime.now().strftime("%Y-%m-%d")
    run_hourly_etl(args.store_id, target_date)
