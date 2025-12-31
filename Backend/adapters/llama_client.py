import httpx
from typing import Dict, Any
from ..settings import settings

async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{settings.LLAMA_URL}/v1/chat/completions", json=payload)
    return {"status": r.status_code, "data": (r.json() if r.headers.get("content-type","").startswith("application/json") else {"raw": r.text})}
