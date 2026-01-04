from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from api.ai_query import router as ai_router
from ai.prompt_template import build_planner_prompt
from ai.call_llm import call_llm
from ai.decision_parser import parse_ai_response
from llama_service import query_llama

app = FastAPI()

# ===== Models =====

class PlannerRequest(BaseModel):
    question: str
    source: str | None = None
    explain: bool = False


class ChatRequest(BaseModel):
    message: str


# ===== Middleware =====

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Chat API (giữ nguyên cho frontend) =====

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return {
        "error": "Chat endpoint is not used in Lesson 6 planner"
    }


# ===== Planner API (CORE of Lesson 6) =====

@app.post("/planner")
async def planner_endpoint(request: PlannerRequest):
    try:
        # 1. Build strict prompt
        prompt = build_planner_prompt(request.question)

        # 2. Call LLM (local, internal)
        llm_output = query_llama(prompt)
        print("=== RAW LLM OUTPUT ===")
        print(llm_output)
        print("======================")
        # 3. Parse + validate JSON instruction
        decision = parse_ai_response(llm_output)

        return {
            "decision": decision
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )



app = FastAPI()

app.include_router(ai_router)
