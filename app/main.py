"""
VNStockAI — FastAPI Backend
"""
import logging
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings, CORS_ORIGINS
from app.routers import stocks, market

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VNStockAI API starting...")
    yield
    logger.info("VNStockAI API shutting down...")


app = FastAPI(
    title="VNStockAI API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api/stocks", tags=["Stocks"])
app.include_router(market.router, prefix="/api/market", tags=["Market"])


@app.get("/")
def root():
    return {"service": "VNStockAI API", "version": "1.0.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(request: Request):
    """Claude AI phân tích cổ phiếu — POST body: {question, context, system}"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    question = body.get("question", "Phân tích cổ phiếu này")
    context  = body.get("context", "")
    system   = body.get("system") or (
        "Bạn là chuyên gia phân tích chứng khoán Việt Nam 15 năm kinh nghiệm. "
        "Phân tích ngắn gọn, súc tích, có số liệu. Dùng bullet points với emoji. "
        "Kết thúc bằng: Khuyến nghị MUA/GIỮ/BÁN + Giá mục tiêu + Stop loss. "
        "Viết bằng tiếng Việt, khoảng 200-250 từ."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "ANTHROPIC_API_KEY chưa cấu hình. Thêm vào Railway Variables."}
        )

    messages = [{"role": "user", "content": f"{context}\n\n{question}".strip()}]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "system": system,
                    "messages": messages,
                }
            )
            data = resp.json()
            analysis = data.get("content", [{}])[0].get("text", "Không có phản hồi")
            return {"analysis": analysis}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi Claude API: {str(e)}"}
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True,
    )
