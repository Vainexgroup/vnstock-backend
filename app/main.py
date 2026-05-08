from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import anthropic

app = FastAPI()

# Mở khóa toàn bộ cho Lovable
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

@app.get("/")
def root():
    return {"message": "Server Việt AI Group đang chạy!"}

@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    
    try:
        # Sử dụng model Sonnet 3.5 với tiền Credit bạn đã có
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            messages=[{"role": "user", "content": f"Phân tích mã {request.symbol}: {request.data}"}]
        )
        return {"analysis": message.content[0].text}
    except Exception as e:
        return {"analysis": f"Lỗi Claude: {str(e)}"}
