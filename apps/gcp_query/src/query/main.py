from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from query.routers import brand, store
from query.config import settings
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TryOps GCP Query API")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(brand.router)
app.include_router(store.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "mock_mode": settings.use_mock_data}

@app.on_event("startup")
def startup_event():
    if settings.use_mock_data:
        logger.warning("Starting in MOCK MODE. BigQuery will not be queried. Mock data disclaimer will be attached to responses.")
