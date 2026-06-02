from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth
from pydantic import BaseModel
from typing import Optional
from .config import settings

# Initialize Firebase Admin
try:
    firebase_admin.get_app()
except ValueError:
    firebase_admin.initialize_app()

security = HTTPBearer()

class UserClaims(BaseModel):
    uid: str
    role: str
    brand_id: str
    store_id: Optional[str] = None

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> UserClaims:
    token = credentials.credentials
    
    if settings.use_mock_data and token.startswith("mock-token-"):
        role = "data_lead"
        store_id = None
        if "store-manager" in token:
            role = "store_manager"
            store_id = "123"
            if "wrong" in token:
                store_id = "999"
                
        return UserClaims(
            uid=token,
            role=role,
            brand_id="brand1",
            store_id=store_id
        )

    try:
        decoded_token = auth.verify_id_token(token)
        # Extract custom claims
        role = decoded_token.get("role")
        brand_id = decoded_token.get("brand_id")
        store_id = decoded_token.get("store_id")

        if not role or not brand_id:
            raise HTTPException(status_code=403, detail="Missing custom claims")

        return UserClaims(
            uid=decoded_token["uid"],
            role=role,
            brand_id=brand_id,
            store_id=store_id
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Expired ID token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

def require_hq_access(user: UserClaims):
    """Ensure user is from HQ (data_lead or merchandiser)"""
    if user.role not in ["data_lead", "merchandiser", "admin"]:
        raise HTTPException(status_code=403, detail="HQ access required")
    return user

def require_store_manager(user: UserClaims):
    """Ensure user is a store manager"""
    if user.role != "store_manager":
        raise HTTPException(status_code=403, detail="Store manager access required")
    if not user.store_id:
        raise HTTPException(status_code=403, detail="Store ID is not assigned to this manager")
    return user
