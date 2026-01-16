import logging
from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Request / Response models
# ============================================================

class AnalyzeRequest(BaseModel):
    """
    Input can be:
    - natural language query (string)
    - semantic JSON (dict)
    """
    query: Union[str, Dict[str, Any]]


class AnalyzeResponse(BaseModel):
    """
    Standard analyze response.
    """
    result: Any
    explanation: Dict[str, Any]


# ============================================================
# Dependency injection
# ============================================================

def get_planner():
    """
    Planner dependency.
    Provided by application bootstrap / wiring layer.

    API layer MUST NOT:
    - construct Planner
    - know Planner internals
    """
    raise NotImplementedError("Planner dependency is not wired")


# ============================================================
# API Endpoint
# ============================================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    planner=Depends(get_planner),
):
    """
    Analyze endpoint.

    Flow:
    - Receive request
    - Delegate to Planner
    - Return result + explanation

    Constraints:
    - No business logic
    - No KPI understanding
    - No data processing
    """

    logger.info("API.analyze.start")

    try:
        planner_result = await planner.execute(
            {
                "query": request.query
            }
        )
    except Exception as exc:
        logger.exception("API.analyze.error")
        raise HTTPException(status_code=500, detail=str(exc))

    response = AnalyzeResponse(
        result=planner_result.get("data"),
        explanation={
            "count": planner_result.get("count"),
        },
    )

    logger.info("API.analyze.done")

    return response
