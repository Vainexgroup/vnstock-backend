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
    if not api_key:
        return {"analysis": "Lỗi: Chưa có API Key trên Railway."}

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"Phân tích mã {request.symbol} với dữ liệu: {request.data}. Nhận định ngắn gọn."

    # Danh sách các model từ cao đến thấp để "thử sai"
    models_to_try = [
        "claude-3-5-sonnet-20240620",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-2.1" # Model đời cũ, cực kỳ dễ kết nối
    ]

    for model_name in models_to_try:
        try:
            message = client.messages.create(
                model=model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return {"analysis": message.content[0].text}
        except Exception as e:
            if "404" in str(e):
                continue # Thử model tiếp theo nếu model này không tìm thấy
            return {"analysis": f"Lỗi API: {str(e)}"}
    
    return {"analysis": "Tất cả các model đều không khả dụng. Vui lòng kiểm tra lại Tier tài khoản Anthropic."}
