import os

PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
VNSTOCK_SOURCE = os.getenv("VNSTOCK_SOURCE", "VCI")

CACHE_TTL_PRICE = 60
CACHE_TTL_HISTORY = 300
CACHE_TTL_INFO = 3600
CACHE_TTL_MARKET = 60

_cors_raw = os.getenv("CORS_ORIGINS", "*")
if _cors_raw.strip() in ("*", '["*"]'):
    CORS_ORIGINS = ["*"]
else:
    CORS_ORIGINS = [s.strip() for s in _cors_raw.split(",") if s.strip()]


class _Settings:
    PORT = PORT
    LOG_LEVEL = LOG_LEVEL
    VNSTOCK_SOURCE = VNSTOCK_SOURCE
    CACHE_TTL_PRICE = CACHE_TTL_PRICE
    CACHE_TTL_HISTORY = CACHE_TTL_HISTORY
    CACHE_TTL_INFO = CACHE_TTL_INFO
    CACHE_TTL_MARKET = CACHE_TTL_MARKET
    CORS_ORIGINS = CORS_ORIGINS


settings = _Settings()
