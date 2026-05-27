from google.cloud import bigquery
from query.config import settings
import logging

logger = logging.getLogger(__name__)

client = None
if not settings.use_mock_data:
    try:
        client = bigquery.Client(project=settings.gcp_project)
    except Exception as e:
        logger.warning(f"Failed to initialize BigQuery client: {e}. Set USE_MOCK_DATA=true for local dev.")

def add_disclaimer(data: dict) -> dict:
    if settings.use_mock_data:
        data["_disclaimer"] = "Mock data - PoC stage only"
    return data

def execute_query(query: str, query_parameters: list) -> list:
    if settings.use_mock_data:
        # Mock mode fallback handled in routers
        return []
        
    job_config = bigquery.QueryJobConfig(
        query_parameters=query_parameters
    )
    
    if not client:
        raise RuntimeError("BigQuery client is not initialized")
        
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()
    return [dict(row) for row in results]
