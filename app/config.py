from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    PORT: int = int(os.getenv("PORT", 8000))
    LOG_LEVEL: str = "INFO"
    VNSTOCK_SOURCE: str = "VCI"

    CACHE_TTL_PRICE: int = 60
    CACHE_TTL_HISTORY: int = 300
    CACHE_TTL_INFO: int = 3600
    CACHE_TTL_MARKET: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# CORS đọc riêng — tránh pydantic parse lỗi List[str] từ env
def get_cors_origins():
    raw = os.getenv("CORS_ORIGINS", "*")
    if raw == "*":
        return ["*"]
    return [s.strip() for s in raw.split(",")]

CORS_ORIGINS = get_cors_origins()
