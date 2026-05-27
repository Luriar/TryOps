import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    use_mock_data: bool = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,https://tryops.pages.dev")
    gcp_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "tryops-prod")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

settings = Settings()
