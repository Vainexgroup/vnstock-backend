from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import anthropic
from vnstock3 import Vnstock

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    symbol: str

@app.get("/health")
def health(): 
    return {"status": "ok"}

@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    
    # 1. Lấy dữ liệu thật từ vnstock
    try:
        stock = Vnstock().stock(symbol=request.symbol, source='VCI')
        ratios = stock.finance.ratio(period='quarter', lang='vi').iloc[0].to_dict()
        price_df = stock.quote.history(start='2026-05-01', end='2026-05-08')
        price_val = price_df.iloc[-1]['close'] if not price_df.empty else "N/A"
        
        real_info = f"Mã: {request.symbol}, Giá: {price_val}, P/E: {ratios.get('P/E')}, ROE: {ratios.get('ROE')}"
    except Exception:
        real_info = f"Mã: {request.symbol} (Dữ liệu sàn đang bảo trì)"
        ratios = {}

    # 2. Gọi AI phân tích (Thử sai để tránh lỗi 404)
    models = ["claude-3-haiku-20240307", "claude-2.1", "claude-instant-1.2"]
    last_error = "Đang đợi Anthropic kích hoạt ví tiền (Tier 1)."

    for model_name in models:
        try:
            message = client.messages.create(
                model=model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": f"Phân tích mã {request.symbol}: {real_info}"}]
            )
            return {
                "analysis": message.content[0].text, 
                "real_stats": ratios
            }
        except Exception as e:
            last_error = str(e)
            continue
            
    # Nếu tất cả model đều lỗi, trả về lỗi thực tế để kiểm tra ví tiền
    return {"analysis": f"Thông báo: {last_error}"}
