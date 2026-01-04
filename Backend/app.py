import os, uuid, time
from fastapi import FastAPI, Header, HTTPException,Request
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from .models.chat import ChatRequest, ChatResponse, Message, Choice
from .settings import settings
from .security import attach_cors, require_bearer
from .middlewares import RequestIDMiddleware, limiter
from slowapi.errors import RateLimitExceeded
from planner.rule_planner import plan
from data_engine.engine import DataEngine
from decision.decision_schema import Decision
from flask import request, jsonify

# chọn adapter
from .adapters import llama_client, ollama_client
# settings.py (đầu file)
print("[CFG] RATE_LIMIT =", settings.RATE_LIMIT)
app = FastAPI(title="Sun Gateway", version="0.1")
attach_cors(app)
app.add_middleware(RequestIDMiddleware)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
def ratelimit_handler(request, exc):
    return JSONResponse(status_code=429, content={"error":"rate_limit_exceeded","detail": str(exc)})

@app.get("/healthz")
def healthz():
    return {"status":"ok","backend": settings.BACKEND, "ts": int(time.time())}

@app.post("/v1/chat/completions")
@limiter.limit(f"{settings.RATE_LIMIT}/minute")
async def chat(request: Request, body: ChatRequest, authorization: str | None = Header(None)):
    api_key = require_bearer(authorization)

    payload = {
        "model": body.model,
        "messages": [m.dict() for m in body.messages],
        "temperature": body.temperature,
        "max_tokens": body.max_tokens
    }

    if settings.BACKEND.lower() == "ollama":
        r = await ollama_client.chat(payload)
    else:
        r = await llama_client.chat(payload)

    if r["status"] != 200:
        raise HTTPException(502, f"Backend error {r['status']}: {r['data']}")

    data = r["data"]
    # Nếu backend đã OpenAI-ish, trả nguyên; nếu là Ollama → đã chuẩn hoá ở adapter.
    if "choices" in data:
        return data
from slowapi.util import get_remote_address



@app.route("/ai/query", methods=["POST"])
def ai_query():
    try:
        body = request.get_json()
        question = body.get("question") if body else None

        if not question:
            return jsonify({"error": "question is required"}), 400

        decision = plan(question)
        engine = DataEngine()
        result = engine.execute(decision)

        return jsonify({
            "decision": decision.dict(),
            "result": result
        })

    except Exception as e:
        # log ra console để docker logs thấy
        print("ERROR in /ai/query:", str(e))
        return jsonify({
            "error": str(e)
        }), 500
