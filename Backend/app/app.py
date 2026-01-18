import os, uuid, time
import re
import logging
import httpx
import unicodedata

from fastapi import FastAPI, Header, HTTPException,Request
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from models.chat import ChatRequest, ChatResponse, Message, Choice
from app.settings import settings
from app.security import attach_cors, require_bearer
from app.middlewares import RequestIDMiddleware, limiter
from slowapi.errors import RateLimitExceeded
from app.planner import planner
from app.planner.planner import Planner as PlannerClass
from app.planner.semantic_resolver import SemanticResolver
from app.planner.decision_engine import DecisionEngine
from app.adapters.mes_api_adapter import ApiDataAdapter
# from data_engine.engine import DataEngine
# from decision.decision_schema import Decision
# chọn adapter
# Adapter và intent parser
from app.adapters import llama_client, ollama_client
from app.intent.intent_pipeline import intent_parser

logger = logging.getLogger(__name__)
# instantiate runtime planner with components (mock adapter for API-first testing)
planner = PlannerClass(SemanticResolver(), DecisionEngine(), ApiDataAdapter())
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
        # Preserve transient LLM loading state (503) so the UI can retry.
        if int(r["status"]) == 503:
            raise HTTPException(
                status_code=503,
                detail={"error": "llm_loading", "upstream": r.get("data")},
                headers={"Retry-After": "2"},
            )
        raise HTTPException(502, f"Backend error {r['status']}: {r['data']}")

    data = r["data"]
    # Nếu backend đã OpenAI-ish, trả nguyên; nếu là Ollama → đã chuẩn hoá ở adapter.
    if "choices" in data:
        return data


@app.post("/analyze")
@limiter.limit(f"{settings.RATE_LIMIT}/minute")
async def analyze(request: Request, authorization: str | None = Header(None)):
    """
    Endpoint nhận input từ User/UI (chat text, query, action request),
    phân tích intent (rule-based + optional LLM),
    lập kế hoạch (Planner/orchestrator),
    gọi proxy API nếu cần, trả kết quả.
    """
    api_key = require_bearer(authorization)
    
    try:
        body = await request.json()
        user_input = body.get("input")
        context = body.get("context") or {}
        if not isinstance(context, dict):
            context = {}
        if not user_input:
            return JSONResponse(status_code=400, content={"error": "input is required"})

        def _parse_ui_command(text: str) -> dict | None:
            """Parse simple UI-only commands so we don't call LLM/MES.

            Frontend can interpret these commands to mutate table rendering.
            """
            t = (text or "").strip()
            if not t:
                return None

            # Hide/remove a column: "Bỏ cột Mã công đoạn đi", "ẩn column process"
            m = re.search(
                r"\b(bỏ|ẩn|xoá|xóa|remove|hide)\s+(cột|column)\s+(?P<col>.+?)\s*(đi|nhé|please|pls)?\s*$",
                t,
                flags=re.IGNORECASE,
            )
            if m:
                col = (m.group("col") or "").strip().strip(".!")
                if col:
                    return {"type": "hide_column", "column": col}

            # Show a column
            m = re.search(
                r"\b(hiện|show|thêm|them|add)\s+(cột|column)\s+(?P<col>.+?)\s*(lên|đi|nhé|please|pls)?\s*$",
                t,
                flags=re.IGNORECASE,
            )
            if m:
                col = (m.group("col") or "").strip().strip(".!")
                if col:
                    return {"type": "show_column", "column": col}

            return None

        def _looks_like_data_request(text: str) -> bool:
            t = (text or "").strip().lower()
            if not t:
                return False

            def _strip_accents(s: str) -> str:
                try:
                    nfkd = unicodedata.normalize("NFD", s)
                    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
                except Exception:
                    return s

            t_ascii = _strip_accents(t)
            # If user is clearly requesting a render-only command, DO NOT treat as data request.
            if re.search(r"\b(chart|graph|plot|vẽ\s*chart|vẽ\s*đồ\s*thị|hiện\s*bảng|show\s*table)\b", t):
                # Render commands are handled in frontend.
                return False
            # UI table commands: hide/remove/show columns, sorting, etc.
            if _parse_ui_command(text) is not None:
                return False
            # Data-ish keywords (vi/en)
            patt = r"(thống\s*kê|báo\s*cáo|report|statistic|statistics|stats|analytics|query|truy\s*vấn|sản\s*lượng|năng\s*suất|productivity|production|output|defect|lỗi|yield|tact|line|by\s+line|per\s+line|dây\s*chuyền|model|by\s+model|per\s+model|factory|from\s+\d{4}|\d+\s*(tháng|month|năm|year)|(?:tháng|thang)\s*\d{1,2}\s*/\s*\d{4}|tỷ\s*lệ|ti\s*lệ|ty\s*le|đạt\s*kế\s*hoạch|dat\s*ke\s*hoach|defect\s*rate|pareto|top\s*\d+|bottom\s*\d+|worst\s*\d+|\bppm\b|통계|생산|생산량|불량|라인|개월)"
            patt_ascii = r"(thong\s*ke|bao\s*cao|truy\s*van|san\s*luong|nang\s*suat|day\s*chuyen|loi|nha\s*may|xuong|report|statistic|statistics|stats|analytics|query|production|output|defect|yield|tact|line|model|factory|from\s+\d{4}|\d+\s*(thang|month|nam|year)|thang\s*\d{1,2}\s*/\s*\d{4}|ti\s*le|ty\s*le|dat\s*ke\s*hoach|defect\s*rate|pareto|top\s*\d+|bottom\s*\d+|worst\s*\d+|\bppm\b)"
            return bool(re.search(patt, t) or re.search(patt_ascii, t_ascii))

        async def _chat_via_llm(text: str) -> str:
            system_prompt = (
                "You are a helpful AI assistant for a Manufacturing Execution System (MES). "
                "Answer naturally and concisely. If the user asks about MES concepts, explain them. "
                "If the user asks general questions (e.g., 'who are you?'), answer normally."
            )
            payload = {
                "model": getattr(settings, "MODEL_NAME", "qwen2-7b"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.7,
                "max_tokens": 256,
            }
            if settings.BACKEND.lower() == "ollama":
                r = await ollama_client.chat(payload)
            else:
                r = await llama_client.chat(payload)
            if r.get("status") != 200:
                raise RuntimeError(f"LLM error {r.get('status')}: {r.get('data')}")
            data = r.get("data") or {}
            try:
                return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
            except Exception:
                return ""

        # ------------------------------------------------------
        # Chat-only path: do NOT call MES / planner for smalltalk
        # ------------------------------------------------------
        ui_cmd = _parse_ui_command(user_input)
        if ui_cmd is not None:
            return JSONResponse(
                content={
                    "user_input": user_input,
                    "intent": {"intent": "ui", "source": "router"},
                    "decision": {"mode": "ui", "viz": "table", "target": None, "ui_command": ui_cmd},
                    "planner_result": {"data": [], "count": 0},
                    "chat_text": "", 
                }
            )

        if not _looks_like_data_request(user_input):
            assistant_text = await _chat_via_llm(user_input)
            return JSONResponse(
                content={
                    "user_input": user_input,
                    "intent": {"intent": "chat", "source": "router"},
                    "decision": {"mode": "chat", "viz": None, "target": None},
                    "planner_result": {"data": [], "count": 0},
                    "chat_text": assistant_text,
                }
            )

        # ------------------------------------------------------
        # Data path requires MES access token (env or per-request)
        # ------------------------------------------------------
        try:
            token_ctx = None
            if isinstance(context, dict):
                token_ctx = (
                    context.get("mesToken")
                    or context.get("mes_token")
                    or context.get("externalApiToken")
                    or context.get("external_api_token")
                )
            token_env = os.getenv("EXTERNAL_API_TOKEN") or os.getenv("MES_API_TOKEN")
            if (not isinstance(token_env, str) or not token_env.strip()) and (
                not isinstance(token_ctx, str) or not token_ctx.strip()
            ):
                return JSONResponse(
                    status_code=502,
                    content={
                        "error": "mes_missing_access_token",
                        "detail": "MES returned UNAUTHORIZED previously. Set EXTERNAL_API_TOKEN in Backend/.env.docker (service mode) or pass context.mesToken (per-request mode).",
                        "request_id": getattr(request.state, "request_id", None),
                    },
                )
        except Exception:
            # Never block on validation logic; planner will handle failures.
            pass
        
        # -----------------------
        # 1️⃣ Intent Parser (LLM + rule-based)
        # -----------------------
        intent = await intent_parser.parse(user_input)
        logger.info(f"[Intent] {intent}")

        # -----------------------
        # 2️⃣ Planner / Orchestrator
        # -----------------------
        # Use Planner orchestration: semantic -> decision -> data -> response
        planner_request = {"user_input": user_input, "intent": intent, "context": context}
        planner_response = await planner.execute(planner_request)
        decision = planner_response
        result = planner_response.get("data", [])
        result_count = None
        try:
            if isinstance(planner_response, dict) and planner_response.get("count") is not None:
                result_count = int(planner_response.get("count"))
        except Exception:
            result_count = None

        debug_payload = None
        if isinstance(context, dict) and context.get("debug") is True:
            try:
                semantic_plan = planner.semantic_resolver.resolve(planner_request)
                execution_plan = planner.decision_engine.decide(semantic_plan)
                # QueryBuilder enriches template fields; decision engine already runs it,
                # but keep this defensive in case wiring changes.
                debug_payload = {
                    "semantic": {
                        "intent": semantic_plan.get("intent"),
                        "entity": semantic_plan.get("entity"),
                        "params": semantic_plan.get("params"),
                    },
                    "execution_plan": {
                        "entity": execution_plan.get("entity"),
                        "action": execution_plan.get("action"),
                        "group_by": execution_plan.get("group_by"),
                        "metrics": execution_plan.get("metrics"),
                        "template_id": execution_plan.get("template_id"),
                        "type": execution_plan.get("type"),
                        "method": execution_plan.get("method"),
                        "endpoint": execution_plan.get("endpoint"),
                        "provides": execution_plan.get("provides"),
                    },
                }

                # Surface planner internal debug if available (env-gated in planner).
                if isinstance(planner_response, dict) and planner_response.get("_debug") is not None:
                    debug_payload["planner"] = planner_response.get("_debug")
            except Exception as _:
                debug_payload = {"error": "debug_plan_failed"}

        # -----------------------
        # 3️⃣ Adapter / Proxy (optional)
        # -----------------------
        # Chat backend integration may be unavailable in test environments;
        # provide a minimal stub instead of failing.
        chat_backend = {"stub": True, "echo": user_input}

        # -----------------------
        # 4️⃣ Return structured response
        # -----------------------
        return JSONResponse(content={
            "user_input": user_input,
            "intent": intent,
            "decision": decision,
            "planner_result": {"data": result, "count": (result_count if result_count is not None else len(result))},
            "chat_backend": chat_backend,
            **({"debug": debug_payload} if debug_payload is not None else {}),
        })
    
    except Exception as e:
        logger.exception("ERROR in /analyze")
        rid = getattr(request.state, "request_id", None)
        msg = str(e) or e.__class__.__name__
        # If the LLM/model is still loading or returning 503, surface a 503 with small Retry-After
        if "loading model" in msg.lower() or "503" in msg or "unavailable" in msg.lower():
            return JSONResponse(
                status_code=503,
                content={"error": "llm_unavailable", "detail": msg, "request_id": rid},
                headers={"Retry-After": "2"},
            )
        if isinstance(e, httpx.TimeoutException) or "readtimeout" in msg.lower() or "timed out" in msg.lower():
            return JSONResponse(
                status_code=504,
                content={"error": "upstream_timeout", "detail": msg, "request_id": rid},
            )
        return JSONResponse(status_code=500, content={"error": "internal_error", "detail": msg, "request_id": rid})