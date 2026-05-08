from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    PORT: int = int(os.getenv("PORT", 8000))
    LOG_LEVEL: str = "INFO"

    # CORS — Railway/Render tự inject $PORT, frontend domain đặt ở đây
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5500",  # VS Code Live Server
        "*",                       # Mở rộng cho dev — thu hẹp lại khi production
    ]

    # Cache TTL (giây)
    CACHE_TTL_PRICE: int = 60       # Giá realtime: 1 phút
    CACHE_TTL_HISTORY: int = 300    # Lịch sử: 5 phút
    CACHE_TTL_INFO: int = 3600      # Thông tin công ty: 1 giờ
    CACHE_TTL_MARKET: int = 60      # Chỉ số thị trường: 1 phút

    # vnstock source ưu tiên: "VCI" | "TCBS" | "SSI"
    VNSTOCK_SOURCE: str = "VCI"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
