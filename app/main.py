"""
VNStockAI — FastAPI Backend
Tích hợp vnstock để lấy dữ liệu HOSE/HNX real-time + lịch sử giá
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings, CORS_ORIGINS
from app.routers import stocks, market

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 VNStockAI API đang khởi động...")
    logger.info(f"   CORS origins: {settings.CORS_ORIGINS}")
    logger.info(f"   Docs: http://localhost:{settings.PORT}/docs")
    yield
    logger.info("👋 VNStockAI API đang tắt...")


app = FastAPI(
    title="VNStockAI API",
    description="""
## API phân tích chứng khoán Việt Nam

**Tính năng:**
- 📊 Dữ liệu lịch sử giá (OHLCV) từ HOSE/HNX/UPCOM
- ⚡ Giá realtime & intraday ticks
- 🏢 Thông tin công ty, báo cáo tài chính
- 📈 Chỉ số thị trường (VN-Index, HNX-Index)
- 🔍 Screener cổ phiếu theo tiêu chí
- 🏆 Top tăng/giảm mạnh nhất

**Nguồn dữ liệu:** vnstock3 (TCBS, VCI, SSI)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(stocks.router, prefix="/api/stocks", tags=["📊 Cổ phiếu"])
app.include_router(market.router, prefix="/api/market", tags=["📈 Thị trường"])


@app.get("/", tags=["🔧 Health"])
def root():
    return {
        "service": "VNStockAI API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "stocks_history": "/api/stocks/{symbol}/history",
            "stocks_price":   "/api/stocks/{symbol}/price",
            "stocks_info":    "/api/stocks/{symbol}/info",
            "stocks_finance": "/api/stocks/{symbol}/financials",
            "screener":       "/api/stocks/screener",
            "market_indices": "/api/market/indices",
            "top_movers":     "/api/market/top-movers",
        }
    }


@app.get("/health", tags=["🔧 Health"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
