from fastapi import APIRouter, Depends, HTTPException
from google.cloud import bigquery
from query.auth import UserClaims, get_current_user, require_store_manager
from query.bigquery_client import execute_query, add_disclaimer
from query.config import settings

router = APIRouter(prefix="/api/v1/store", tags=["Store"])

@router.get("/{store_id}/status")
def get_store_status(store_id: str, user: UserClaims = Depends(get_current_user)):
    # Both HQ and Store Manager can view this, BUT if store manager, they can only view THEIR store
    if user.role == "store_manager" and user.store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to other stores")
    
    if settings.use_mock_data:
        return add_disclaimer({
            "brand_id": user.brand_id,
            "store_id": store_id,
            "rooms": [
                {"id": 1, "status": "empty", "duration": 0},
                {"id": 2, "status": "warning", "duration": 8, "message": f"Needs assistance at {store_id}"}
            ]
        })

    query = """
        SELECT *
        FROM `tryops_data.raw_events`
        WHERE brand_id = @brand_id AND store_id = @store_id
        ORDER BY batch_start DESC
        LIMIT 10
    """
    params = [
        bigquery.ScalarQueryParameter("brand_id", "STRING", user.brand_id),
        bigquery.ScalarQueryParameter("store_id", "STRING", store_id)
    ]
    results = execute_query(query, params)
    return add_disclaimer({"rooms": results})

@router.get("/{store_id}/manager-data")
def get_manager_data(store_id: str, user: UserClaims = Depends(get_current_user)):
    # Only store manager can view this data (Shield Data) - Block HQ admins
    require_store_manager(user)
    
    if user.store_id != store_id:
        raise HTTPException(status_code=403, detail="Access denied to other stores")
    
    if settings.use_mock_data:
        return add_disclaimer({
            "brand_id": user.brand_id,
            "store_id": store_id,
            "assistance_conversion": 42,
            "no_assistance_conversion": 22
        })

    query = """
        SELECT avg(conversion)
        FROM `tryops_data.joint_signals`
        WHERE brand_id = @brand_id AND store_id = @store_id
    """
    params = [
        bigquery.ScalarQueryParameter("brand_id", "STRING", user.brand_id),
        bigquery.ScalarQueryParameter("store_id", "STRING", store_id)
    ]
    results = execute_query(query, params)
    return add_disclaimer({"stats": results})
