import os
from dataclasses import dataclass

@dataclass
class Config:
    """Store Gateway Configuration."""
    
    # Store Identifier
    STORE_ID: str = os.getenv("STORE_ID", "store_default")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    
    # Cloud Run Ingest Endpoint
    INGEST_URL: str = os.getenv("INGEST_URL", "http://localhost:8080/ingest")
    
    # GCP Service Account JSON key path (for OIDC token generation)
    GCP_SA_KEY_PATH: str = os.getenv("GCP_SA_KEY_PATH", "")
    
    # SQLCipher Encryption Key
    SQLCIPHER_KEY: str = os.getenv("SQLCIPHER_KEY", "")
    DEV_FALLBACK_KEY: str = os.getenv("DEV_FALLBACK_KEY", "local-dev-fallback-key")
    
    # SQLite DB Path
    DB_PATH: str = os.getenv("DB_PATH", "gateway.db")
    
    # MQTT Broker config (usually running locally on the Pi via Mosquitto)
    MQTT_HOST: str = os.getenv("MQTT_HOST", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    
    # POS Polling URL (if applicable)
    POS_API_URL: str = os.getenv("POS_API_URL", "http://localhost:8081/pos/api")
    
    # Server Binding
    HTTP_HOST: str = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT: int = int(os.getenv("HTTP_PORT", "5000"))

config = Config()
