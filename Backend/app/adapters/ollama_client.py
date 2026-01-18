from __future__ import annotations

from typing import Any, Dict

import asyncio

import time

import httpx

from ..settings import settings


def map_openai_to_ollama(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model": payload.get("model"),
        "messages": payload.get("messages"),
        "options": {
            "temperature": payload.get("temperature", 0.7),
            "num_predict": payload.get("max_tokens", 256),
        },
    }


def _json_or_raw(r: httpx.Response) -> Dict[str, Any]:
    ctype = (r.headers.get("content-type") or "").lower()
    if ctype.startswith("application/json"):
        try:
            return r.json()
        except Exception:
            return {"raw": r.text}
    return {"raw": r.text}


def _is_loading_model(status_code: int, body: Dict[str, Any]) -> bool:
    if status_code != 503:
        return False
    try:
        msg = None
        if isinstance(body, dict):
            err = body.get("error")
            if isinstance(err, dict):
                msg = err.get("message")
            if not msg:
                msg = body.get("message") or body.get("raw")
        return isinstance(msg, str) and "loading" in msg.lower() and "model" in msg.lower()
    except Exception:
        return False


async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy OpenAI-ish payload to Ollama /api/chat and normalize response."""
    mapped = map_openai_to_ollama(payload)

    max_attempts = 6
    delay_seconds = 1.0
    delay_cap = 4.0

    async with httpx.AsyncClient(timeout=120) as client:
        last_status = 503
        last_body: Dict[str, Any] = {"error": {"message": "Loading model"}}
        for attempt in range(1, max_attempts + 1):
            r = await client.post(f"{settings.OLLAMA_URL}/api/chat", json=mapped)
            body = _json_or_raw(r)
            if _is_loading_model(r.status_code, body) and attempt < max_attempts:
                await asyncio.sleep(min(delay_seconds, delay_cap))
                delay_seconds = min(delay_seconds * 2, delay_cap)
                last_status, last_body = r.status_code, body
                continue
            # Continue existing normalization logic below.
            break

    if r.status_code != 200:
        return {"status": r.status_code, "data": body}

    d = body
    text = (d.get("message") or {}).get("content") or ""

    norm = {
        "id": "chatcmpl-ollama",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": mapped.get("model"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
    }
    return {"status": 200, "data": norm}


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
