from pydantic_settings import BaseSettings
from typing import List
import os
import json


class Settings(BaseSettings):
    PORT: int = int(os.getenv("PORT", 8000))
    LOG_LEVEL: str = "INFO"
    VNSTOCK_SOURCE: str = "VCI"

    # Fix CORS — đọc từ env hoặc dùng default
    @property
    def CORS_ORIGINS(self) -> List[str]:
        raw = os.getenv("CORS_ORIGINS", "*")
        if raw == "*":
            return ["*"]
        try:
            return json.loads(raw)
        except Exception:
            return [s.strip() for s in raw.split(",")]

    CACHE_TTL_PRICE: int = 60
    CACHE_TTL_HISTORY: int = 300
    CACHE_TTL_INFO: int = 3600
    CACHE_TTL_MARKET: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
