from fastapi import FastAPI, HTTPException
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

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"analysis": "Lỗi: Chưa cấu hình ANTHROPIC_API_KEY trên Railway."}

    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        prompt = f"Bạn là chuyên gia tài chính Việt AI Group. Hãy phân tích mã {request.symbol} với dữ liệu: {request.data}. Nhận định ngắn gọn, súc tích."
        
        # Dùng model Sonnet 3 chính thống của Anthropic
        message = client.messages.create(
            model="claude-3-sonnet-20240229", 
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"analysis": message.content[0].text}
    except Exception as e:
        # Nếu vẫn lỗi 404, thử dùng model Haiku (nhẹ nhất, chắc chắn có)
        if "404" in str(e):
             try:
                 message = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}]
                 )
                 return {"analysis": message.content[0].text}
             except Exception as e2:
                 return {"analysis": f"Lỗi hệ thống Claude: {str(e2)}"}
        return {"analysis": f"Lỗi: {str(e)}"}
