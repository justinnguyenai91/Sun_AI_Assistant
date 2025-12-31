import httpx
from typing import Dict, Any
from ..settings import settings

def map_openai_to_ollama(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model": payload.get("model"),
        "messages": payload.get("messages"),
        "options": {
            "temperature": payload.get("temperature", 0.7),
            "num_predict": payload.get("max_tokens", 256)
        }
    }

async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    mapped = map_openai_to_ollama(payload)
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{settings.OLLAMA_URL}/api/chat", json=mapped)
    # Chuẩn hoá về OpenAI-ish:
    if r.status_code == 200:
        d = r.json()
        text = d.get("message",{}).get("content","")
        norm = {
            "id": "chatcmpl-ollama",
            "object": "chat.completion",
            "created": __import__("time").time().__int__(),
            "model": mapped["model"],
            "choices": [{"index":0,"message":{"role":"assistant","content":text},"finish_reason":"stop"}],
            "usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
        }
        return {"status": 200, "data": norm}
    return {"status": r.status_code, "data": {"raw": r.text}}
