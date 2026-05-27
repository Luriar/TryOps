import pytest
from fastapi.testclient import TestClient
from query.main import app
from query.auth import get_current_user, UserClaims
from fastapi import HTTPException

client = TestClient(app)

# --- Mocks ---

def override_get_current_user_hq():
    return UserClaims(uid="user123", role="data_lead", brand_id="test_brand")

def override_get_current_user_store_manager():
    return UserClaims(uid="user456", role="store_manager", brand_id="test_brand", store_id="store_001")

def override_get_current_user_store_manager_2():
    return UserClaims(uid="user789", role="store_manager", brand_id="test_brand", store_id="store_002")

def override_get_current_user_unauthorized():
    raise HTTPException(status_code=401, detail="Invalid token")


# --- Tests ---

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

def test_unauthorized_access():
    app.dependency_overrides[get_current_user] = override_get_current_user_unauthorized
    response = client.get("/api/v1/brand/insights")
    assert response.status_code == 401
    app.dependency_overrides = {}

def test_brand_insights_hq_access_success():
    app.dependency_overrides[get_current_user] = override_get_current_user_hq
    response = client.get("/api/v1/brand/insights")
    assert response.status_code == 200
    assert "_disclaimer" in response.json()
    app.dependency_overrides = {}

def test_brand_insights_store_manager_forbidden():
    app.dependency_overrides[get_current_user] = override_get_current_user_store_manager
    response = client.get("/api/v1/brand/insights")
    assert response.status_code == 403
    assert "HQ access required" in response.json()["detail"]
    app.dependency_overrides = {}

def test_store_status_access():
    # HQ can access
    app.dependency_overrides[get_current_user] = override_get_current_user_hq
    res1 = client.get("/api/v1/store/store_001/status")
    assert res1.status_code == 200

    # Store manager 1 can access store 1
    app.dependency_overrides[get_current_user] = override_get_current_user_store_manager
    res2 = client.get("/api/v1/store/store_001/status")
    assert res2.status_code == 200

    # Store manager 1 CANNOT access store 2
    res3 = client.get("/api/v1/store/store_002/status")
    assert res3.status_code == 403
    app.dependency_overrides = {}

def test_manager_data_access():
    # HQ CANNOT access (blocked by require_store_manager)
    app.dependency_overrides[get_current_user] = override_get_current_user_hq
    res1 = client.get("/api/v1/store/store_001/manager-data")
    assert res1.status_code == 403
    assert "Store manager access required" in res1.json()["detail"]

    # Store manager 1 CAN access store 1
    app.dependency_overrides[get_current_user] = override_get_current_user_store_manager
    res2 = client.get("/api/v1/store/store_001/manager-data")
    assert res2.status_code == 200

    # Store manager 1 CANNOT access store 2
    res3 = client.get("/api/v1/store/store_002/manager-data")
    assert res3.status_code == 403
    app.dependency_overrides = {}
