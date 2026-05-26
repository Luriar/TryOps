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

def run_monthly_etl(target_month: str):
    """
    HQ Dashboard 용 월간 리포트 마트 생성
    target_month: 'YYYY-MM' 형식
    """
    logger.info(f"Starting monthly ETL for {target_month}")
    
    project_id = os.getenv("PROJECT_ID", "tryops-stage0")
    client = bigquery.Client(project=project_id)
    
    query = f"""
        SELECT *
        FROM `tryops_data.mart_daily_store_summary`
        WHERE FORMAT_DATE('%Y-%m', target_date) = '{target_month}'
    """
    
    try:
        df_arrow = client.query(query).to_arrow()
        df = pl.from_arrow(df_arrow)
    except Exception as e:
        logger.warning(f"BQ Fetch failed. Error: {e}")
        df = pl.DataFrame()
        
    if df.is_empty():
        logger.info("No data for monthly aggregation. Exiting.")
        return
        
    con = duckdb.connect()
    con.register("daily_mart", df)
    
    monthly_mart_df = con.execute("""
        SELECT 
            store_id,
            STRFTIME(target_date, '%Y-%m') as target_month,
            SUM(total_sessions) as monthly_total_sessions,
            AVG(avg_duration) as monthly_avg_duration,
            AVG(avg_hesitation) as monthly_avg_hesitation,
            SUM(high_hesitation_count) as monthly_high_hesitation_count,
            CURRENT_TIMESTAMP as etl_processed_at
        FROM daily_mart
        GROUP BY 1, 2
    """).pl()
    
    # 파티션 방식 변경: 월단위 적재
    partition_suffix = target_month.replace('-', '') + "01" # 강제로 1일자로 마스킹
    load_to_mart("mart_monthly_hq_report", monthly_mart_df, partition_suffix)
    logger.info("Monthly ETL completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TryOps Monthly ETL")
    parser.add_argument("--month", required=False, help="Target Month (YYYY-MM)")
    args = parser.parse_args()
    
    target_month = args.month if args.month else datetime.now().strftime("%Y-%m")
    run_monthly_etl(target_month)
