from __future__ import annotations

from typing import Any, Dict

import asyncio

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


def _is_loading_model(status_code: int, body: Dict[str, Any]) -> bool:
    if status_code != 503:
        return False
    try:
        # llama.cpp often returns: {"error": {"message": "Loading model", ...}}
        err = body.get("error") if isinstance(body, dict) else None
        msg = None
        if isinstance(err, dict):
            msg = err.get("message")
        if not msg and isinstance(body, dict):
            msg = body.get("message")
        if not msg and isinstance(body, dict):
            msg = body.get("raw")
        return isinstance(msg, str) and "loading model" in msg.lower()
    except Exception:
        return False


async def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy OpenAI-compatible chat/completions to llama.cpp server."""

    # llama.cpp can return transient 503 "Loading model" during startup/warmup.
    # Handle it here so upstream callers don't need bespoke retry logic.
    max_attempts = 8
    delay_seconds = 1.0
    delay_cap = 5.0

    async with httpx.AsyncClient(timeout=120) as client:
        last_status = 503
        last_body: Dict[str, Any] = {"error": {"message": "Loading model"}}

        for attempt in range(1, max_attempts + 1):
            r = await client.post(f"{settings.LLAMA_URL}/v1/chat/completions", json=payload)
            body = _json_or_raw(r)
            if _is_loading_model(r.status_code, body) and attempt < max_attempts:
                await asyncio.sleep(min(delay_seconds, delay_cap))
                delay_seconds = min(delay_seconds * 2, delay_cap)
                last_status, last_body = r.status_code, body
                continue
            return {"status": r.status_code, "data": body}

        return {"status": last_status, "data": last_body}


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
