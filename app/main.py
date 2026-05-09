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
def health(): return {"status": "ok"}

@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        # Lấy dữ liệu thật cho mã bất kỳ (VCB, BID, HPG...)
        stock = Vnstock().stock(symbol=request.symbol, source='VCI')
        ratios = stock.finance.ratio(period='quarter', lang='vi').iloc[0].to_dict()
        price = stock.quote.history(start='2026-05-01', end='2026-05-08').iloc[-1].to_dict()
        
        real_data = f"Mã: {request.symbol}, Giá: {price['close']}, P/E: {ratios.get('P/E')}, ROE: {ratios.get('ROE')}"
    except:
        real_data = "Dữ liệu sàn đang bảo trì."

    # Danh sách thử sai model để tránh lỗi 404
    for model_name in ["claude-3-haiku-20240307", "claude-2.1"]:
        try:
            msg = client.messages.create(
                model=model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": f"Phân tích chuyên sâu mã này: {real_data}"}]
            )
            return {"analysis": msg.content[0].text, "real_stats": ratios}
        except:
            continue
    return {"analysis": "Đang đợi Anthropic kích hoạt ví tiền (Tier 1)."}
# Sửa đoạn cuối cùng trong hàm analyze_stock
    except Exception as e:
        last_error = str(e)
        continue
            
    # Thay dòng "Đang đợi..." bằng dòng này để xem lỗi thật
    return {"analysis": f"Lỗi thực tế từ Anthropic: {last_error}"}
