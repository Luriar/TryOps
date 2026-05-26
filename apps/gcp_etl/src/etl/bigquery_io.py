import os
import logging
from typing import Dict, Any
import polars as pl
from google.cloud import bigquery

logger = logging.getLogger(__name__)

project_id = os.getenv("PROJECT_ID", "tryops-stage0")
client = bigquery.Client(project=project_id)

def fetch_raw_events(store_id: str, target_date: str) -> Dict[str, pl.DataFrame]:
    """
    BigQuery Storage API를 사용하여 특정 일자의 raw_events 데이터를 Polars로 고속 로드.
    (로컬 테스트 시 Mock 데이터를 생성하도록 처리 가능)
    """
    # 실제 운영 시 쿼리
    query = f"""
        SELECT *
        FROM `tryops_data.raw_events`
        WHERE store_id = '{store_id}' 
          AND DATE(batch_start) = '{target_date}'
    """
    
    logger.info(f"Fetching raw events for {store_id} on {target_date}")
    
    try:
        # to_arrow() -> from_arrow() is the fastest path from BQ to Polars
        df_arrow = client.query(query).to_arrow()
        df = pl.from_arrow(df_arrow)
        
        # Split JSON array fields into separate dataframes for processing
        # In a real environment, csi_aggregates/rfid_events would be UNNESTed.
        return {"raw": df}
    except Exception as e:
        logger.warning(f"BigQuery fetch failed, returning empty Mock DataFrame. Error: {e}")
        return {
            "raw": pl.DataFrame()
        }

def load_to_mart(table_name: str, df: pl.DataFrame, partition_date: str):
    """
    DuckDB나 Polars에서 가공 완료된 마트 데이터를 BigQuery에 적재.
    파티션 교체(REPLACE) 방식을 사용하여 멱등성 보장.
    """
    if df.is_empty():
        logger.info(f"Empty dataframe, skipping load to {table_name}")
        return
        
    table_id = f"{project_id}.tryops_data.{table_name}${partition_date.replace('-', '')}"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE", # 덮어쓰기 (멱등성 보장)
        source_format=bigquery.SourceFormat.PARQUET,
    )
    
    # Save Polars to temporary parquet
    temp_path = f"/tmp/{table_name}_{partition_date}.parquet"
    df.write_parquet(temp_path)
    
    logger.info(f"Loading {len(df)} rows to {table_id}")
    try:
        with open(temp_path, "rb") as source_file:
            job = client.load_table_from_file(source_file, table_id, job_config=job_config)
        job.result()  # Wait for the job to complete
        logger.info(f"Loaded successfully to {table_name}")
    except Exception as e:
        logger.error(f"Failed to load data to BigQuery: {e}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
