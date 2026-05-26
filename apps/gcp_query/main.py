# TryOps Query API (FastAPI)
from fastapi import FastAPI

app = FastAPI(title="TryOps GCP Query API")

@app.get("/metrics/stores/{store_id}")
async def get_store_metrics(store_id: str, date: str):
    # TODO: Query BigQuery and return aggregated metrics (fitting count, conversion rate)
    return {
        "store_id": store_id,
        "date": date,
        "fitting_count": 120,
        "conversion_rate": 0.15
    }
