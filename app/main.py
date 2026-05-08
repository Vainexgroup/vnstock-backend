from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import anthropic

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
    data: dict

# ĐOẠN NÀY LÀ ĐỂ FIX LỖI 404 TRONG LOG CỦA BẠN
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Viet AI Group Online"}

@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    try:
        # Dùng model cao cấp cho tài khoản đã nạp tiền
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            messages=[{"role": "user", "content": f"Phân tích mã {request.symbol} với dữ liệu: {request.data}"}]
        )
        # Thay đổi dòng này trong file main.py của bạn
        message = client.messages.create(
            model="claude-2.1", 
            max_tokens=1024,
            messages=[{"role": "user", "content": f"Phân tích mã {request.symbol}: {request.data}"}]
        )
        return {"analysis": message.content[0].text}
    except Exception as e:
        return {"analysis": f"Lỗi Claude: {str(e)}"}
