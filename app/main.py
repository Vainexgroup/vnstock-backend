from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import anthropic

app = FastAPI()

# Mở khóa để Lovable truy cập được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình để Backend hiểu dữ liệu Lovable gửi sang
class AnalysisRequest(BaseModel):
    symbol: str
    data: dict

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"analysis": "Lỗi: Bạn chưa cấu hình ANTHROPIC_API_KEY trên Railway."}

    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        # Gửi dữ liệu sang cho Claude xử lý
        prompt = f"Phân tích mã chứng khoán {request.symbol} với dữ liệu này: {request.data}. Trả về nhận định ngắn gọn, súc tích."
        
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"analysis": message.content[0].text}
    except Exception as e:
        return {"analysis": f"Lỗi kết nối Claude: {str(e)}"}
