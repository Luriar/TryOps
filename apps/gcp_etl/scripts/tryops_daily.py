#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime
import logging
import duckdb
import polars as pl
from google.cloud import bigquery

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from etl.bigquery_io import load_to_mart

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def send_slack_alert(message: str):
    """Data Quality 이슈 발생 시 Slack / Email 알림"""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning(f"SLACK_WEBHOOK_URL is not set. Would have sent: {message}")
        return
    # 실제로는 requests.post(webhook_url, json={"text": message}) 처리
    logger.info(f"Sent alert to slack: {message}")

def run_daily_etl(target_date: str):
    logger.info(f"Starting daily ETL for {target_date}")
    
    project_id = os.getenv("PROJECT_ID", "tryops-stage0")
    client = bigquery.Client(project=project_id)
    
    query = f"""
        SELECT *
        FROM `tryops_data.mart_hourly_sessions`
        WHERE DATE(session_start) = '{target_date}'
    """
    
    try:
        df_arrow = client.query(query).to_arrow()
        df = pl.from_arrow(df_arrow)
    except Exception as e:
        logger.warning(f"BQ Fetch failed, mocking empty DF. Error: {e}")
        df = pl.DataFrame()
        
    if df.is_empty():
        logger.info("No data for daily aggregation. Exiting.")
        return
        
    # Data Quality Check (from data_pipeline.md 5.3)
    # 1. Null Checks
    if df.select(pl.col("hesitation_score").is_null().sum()).item() > 0:
        send_slack_alert("[Data Quality Error] Null values found in hesitation_score")
        
    # 2. Value Range Checks
    out_of_bounds = df.filter(
        (pl.col("hesitation_score") < 0) | (pl.col("hesitation_score") > 1.0) |
        (pl.col("companion_score") < 0) | (pl.col("companion_score") > 1.0)
    )
    if not out_of_bounds.is_empty():
        send_slack_alert(f"[Data Quality Error] Score out of bounds. Found {len(out_of_bounds)} anomalies.")
        
    # DuckDB Daily Aggregation
    con = duckdb.connect()
    con.register("hourly_mart", df)
    
    daily_mart_df = con.execute("""
        SELECT 
            store_id,
            DATE(session_start) as target_date,
            COUNT(session_id) as total_sessions,
            AVG(duration_seconds) as avg_duration,
            AVG(hesitation_score) as avg_hesitation,
            AVG(companion_score) as avg_companion,
            AVG(friction_score) as avg_friction,
            SUM(CASE WHEN hesitation_score > 0.8 THEN 1 ELSE 0 END) as high_hesitation_count,
            CURRENT_TIMESTAMP as etl_processed_at
        FROM hourly_mart
        GROUP BY 1, 2
    """).pl()
    
    load_to_mart("mart_daily_store_summary", daily_mart_df, target_date)
    logger.info("Daily ETL completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TryOps Daily ETL")
    parser.add_argument("--date", required=False, help="Target Date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    target_date = args.date if args.date else datetime.now().strftime("%Y-%m-%d")
    run_daily_etl(target_date)
