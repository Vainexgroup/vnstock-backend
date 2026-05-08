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

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze_stock(request: AnalysisRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)
    
    # Chúng ta sẽ thử dùng model Haiku (Rất thông minh và dễ mở cho tài khoản mới)
    # Nếu Haiku vẫn lỗi, nó sẽ tự lùi về model đời cũ hơn nữa để chắc chắn chạy được.
    
    models = ["claude-3-haiku-20240307", "claude-2.1", "claude-instant-1.2"]
    
    for model_name in models:
        try:
            message = client.messages.create(
                model=model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": f"Phân tích mã {request.symbol} dựa trên: {request.data}"}]
            )
            return {"analysis": message.content[0].text}
        except Exception as e:
            # Nếu model này lỗi, nó sẽ bỏ qua và thử model tiếp theo trong danh sách
            last_error = str(e)
            continue
            
    return {"analysis": f"Lỗi hệ thống Anthropic: {last_error}. Vui lòng đợi vài phút để tiền nạp được kích hoạt."}
