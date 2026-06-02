import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from query.auth import get_current_user, UserClaims, require_hq_access, require_store_manager
from firebase_admin import auth

def test_get_current_user_success(monkeypatch):
    def mock_verify(*args, **kwargs):
        return {"uid": "user123", "role": "data_lead", "brand_id": "brand1"}
    monkeypatch.setattr(auth, "verify_id_token", mock_verify)
    
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="abc")
    user = get_current_user(creds)
    assert user.uid == "user123"
    assert user.role == "data_lead"

def test_get_current_user_missing_claims(monkeypatch):
    def mock_verify(*args, **kwargs):
        return {"uid": "user123"}
    monkeypatch.setattr(auth, "verify_id_token", mock_verify)
    
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="abc")
    with pytest.raises(HTTPException) as exc:
        get_current_user(creds)
    assert exc.value.status_code == 401

def test_get_current_user_invalid_token(monkeypatch):
    def mock_verify(*args, **kwargs):
        raise auth.InvalidIdTokenError("invalid")
    monkeypatch.setattr(auth, "verify_id_token", mock_verify)
    
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="abc")
    with pytest.raises(HTTPException) as exc:
        get_current_user(creds)
    assert exc.value.status_code == 401

def test_get_current_user_expired_token(monkeypatch):
    def mock_verify(*args, **kwargs):
        raise auth.ExpiredIdTokenError("expired")
    monkeypatch.setattr(auth, "verify_id_token", mock_verify)
    
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="abc")
    with pytest.raises(HTTPException) as exc:
        get_current_user(creds)
    assert exc.value.status_code == 401

def test_get_current_user_exception(monkeypatch):
    def mock_verify(*args, **kwargs):
        raise Exception("generic")
    monkeypatch.setattr(auth, "verify_id_token", mock_verify)
    
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="abc")
    with pytest.raises(HTTPException) as exc:
        get_current_user(creds)
    assert exc.value.status_code == 401

def test_require_hq_access():
    user = UserClaims(uid="1", role="data_lead", brand_id="1")
    assert require_hq_access(user) == user
    
    with pytest.raises(HTTPException):
        require_hq_access(UserClaims(uid="2", role="store_manager", brand_id="1"))

def test_require_store_manager():
    user = UserClaims(uid="1", role="store_manager", brand_id="1", store_id="S1")
    assert require_store_manager(user) == user
    
    with pytest.raises(HTTPException):
        require_store_manager(UserClaims(uid="2", role="data_lead", brand_id="1"))
        
    with pytest.raises(HTTPException):
        require_store_manager(UserClaims(uid="3", role="store_manager", brand_id="1")) # no store_id
