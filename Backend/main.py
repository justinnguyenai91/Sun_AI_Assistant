from fastapi import FastAPI
from pydantic import BaseModel
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI()

# Cho phép frontend (React) truy cập backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tạm cho phép tất cả, có thể đổi thành ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dữ liệu đầu vào từ frontend
class ChatRequest(BaseModel):
    message: str


# API chat
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message  # Lấy dữ liệu người dùng gửi lên

    # gửi đến model Qwen (llama-server đang chạy tại port 8080)
    payload = {
        "model": "qwen2-7b",
        "messages": [
            {"role": "system", "content": "Bạn là trợ lý AI thông minh, giao tiếp tự nhiên, và ưu tiên giải thích rõ ràng, dễ hiểu."},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,   # kiểm soát độ sáng tạo
        "top_p": 0.9,         # kiểm soát độ ngẫu nhiên
        "max_tokens": 512     # tránh bị cắt câu
    }

    response = requests.post("http://model:8080/v1/chat/completions", json=payload)

    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return {"reply": content}
    else:
        return {"error": response.text}
