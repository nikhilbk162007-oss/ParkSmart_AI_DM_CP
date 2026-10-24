import os
import json
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application runtime configuration loaded from environment variables and .env file.
    """
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    
    # CORS Origins: in production defaults to empty or specific domain;
    # allows local frontend dev when configured.
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ]
    
    # MongoDB configuration
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "parksmart_ai"
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 2000
    
    # Integration Adapters configuration
    # Modes: "mock" (baseline simulation), "module" (python import), "http" (microservice)
    ML_ADAPTER_MODE: str = "mock"
    ML_SERVICE_URL: str = "http://localhost:8001"
    ML_TIMEOUT_SECONDS: float = 3.0
    
    REC_ADAPTER_MODE: str = "mock"
    REC_SERVICE_URL: str = "http://localhost:8002"
    REC_TIMEOUT_SECONDS: float = 3.0

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
