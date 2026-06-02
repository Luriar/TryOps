from fastapi import APIRouter, Depends
from google.cloud import bigquery
from query.auth import UserClaims, get_current_user, require_hq_access
from query.bigquery_client import execute_query, add_disclaimer
from query.config import settings

router = APIRouter(prefix="/api/v1/brand", tags=["Brand"])

@router.get("/insights")
def get_brand_insights(user: UserClaims = Depends(get_current_user)):
    require_hq_access(user)
    
    if settings.use_mock_data:
        return add_disclaimer({
            "brand_id": user.brand_id,
            "insights": [
                {"message": f"[{user.brand_id}] SKU_LEGGINGS_M_BLACK: Hesitation 0.78 (High)", "type": "warning"},
                {"message": f"[{user.brand_id}] Gangnam Store fitting friction 0.85", "type": "alert"}
            ],
            "skuData": [
                {"name": f"{user.brand_id}-SKU-001", "tryOn": 87, "conversion": 24, "hesitation": 0.78}
            ]
        })

    # Parameterized query enforcement
    query = """
        SELECT sku_id, sum(fitting_friction) as total_friction
        FROM `tryops_data.joint_signals`
        WHERE brand_id = @brand_id
        GROUP BY sku_id
        LIMIT 10
    """
    params = [
        bigquery.ScalarQueryParameter("brand_id", "STRING", user.brand_id)
    ]
    results = execute_query(query, params)
    return add_disclaimer({"insights": results, "skuData": []})

@router.get("/sku/{sku_id}")
def get_sku_detail(sku_id: str, user: UserClaims = Depends(get_current_user)):
    require_hq_access(user)
    
    if settings.use_mock_data:
        return add_disclaimer({
            "brand_id": user.brand_id,
            "sku_id": sku_id,
            "tryOn": 87,
            "tryOnTrend": 16,
            "conversion": 24,
            "conversionTrend": -7,
            "hesitation": 0.78,
            "companion": 12
        })

    query = """
        SELECT *
        FROM `tryops_data.joint_signals`
        WHERE brand_id = @brand_id AND sku_id = @sku_id
        LIMIT 1
    """
    params = [
        bigquery.ScalarQueryParameter("brand_id", "STRING", user.brand_id),
        bigquery.ScalarQueryParameter("sku_id", "STRING", sku_id)
    ]
    results = execute_query(query, params)
    return add_disclaimer({"data": results})
