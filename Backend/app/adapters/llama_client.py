from __future__ import annotations

from typing import Any, Dict

import httpx

from ..settings import settings


def _json_or_raw(r: httpx.Response) -> Dict[str, Any]:
    ctype = (r.headers.get("content-type") or "").lower()
    if ctype.startswith("application/json"):
        try:
            return r.json()
        except Exception:
            return {"raw": r.text}
    return {"raw": r.text}


async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy OpenAI-compatible chat/completions to llama.cpp server."""
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{settings.LLAMA_URL}/v1/chat/completions", json=payload)
    return {"status": r.status_code, "data": _json_or_raw(r)}


async def complete(prompt: str) -> str:
    """Convenience helper used by intent parsing and simple chat prompts."""
    payload = {
        "model": getattr(settings, "MODEL_NAME", "qwen2-7b"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 256,
    }
    r = await chat(payload)
    if r.get("status") != 200:
        raise RuntimeError(f"LLM error {r.get('status')}: {r.get('data')}")

    data = r.get("data") or {}
    try:
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    except Exception:
        return ""
