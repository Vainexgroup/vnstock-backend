from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import os

app = FastAPI()
@app.get("/health")
def health_check():
    return {"status": "ok"}
# Cấu hình để Lovable có thể truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ĐỊNH DẠNG DỮ LIỆU (Bắt buộc phải có)
class AnalysisRequest(BaseModel):
    symbol: str
    data: dict

@app.get("/")
async def root():
    return {"message": "VNStockAI API is Live"}

# ĐƯỜNG DẪN PHÂN TÍCH AI (Endpoint)
@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Thiếu cấu hình ANTHROPIC_API_KEY trên Railway")
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"Phân tích cổ phiếu {request.symbol} với dữ liệu: {request.data}. Đưa ra nhận định ngắn gọn."
        
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"analysis": message.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
