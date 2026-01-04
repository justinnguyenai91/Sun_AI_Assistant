from settings import settings
import httpx

async def chat(messages):
    if settings.BACKEND == "llama":
        url = f"{settings.LLAMA_URL}/v1/chat/completions"
    elif settings.BACKEND == "ollama":
        url = f"{settings.OLLAMA_URL}/api/chat"
    else:
        raise RuntimeError("Unsupported BACKEND")

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json={
            "messages": messages,
            "temperature": 0,
        })
        r.raise_for_status()
        return r.json()

async def query_llama(messages):
    return await chat(messages)
