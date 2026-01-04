from fastapi import APIRouter
from pydantic import BaseModel

from planner.rule_planner import plan
from data_engine.engine import DataEngine

router = APIRouter(prefix="/ai", tags=["AI"])

class QueryRequest(BaseModel):
    question: str

@router.post("/query")
def ai_query(req: QueryRequest):
    decision = plan(req.question)
    engine = DataEngine(decision.datasource)
    result = engine.execute(decision)
    if hasattr(result, "to_dict"):
        result = result.to_dict(orient="records")
    return {
        "decision": decision.dict(),
        "result": result
    }
