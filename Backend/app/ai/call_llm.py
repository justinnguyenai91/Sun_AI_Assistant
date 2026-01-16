import requests
import os


LLM_BASE_URL = os.getenv("AI_MODEL_URL", "http://model:8080")


def call_llm(messages: list, temperature=0, max_tokens=512) -> str:
    """
    Call local LLM (llama.cpp server - OpenAI compatible)
    """

    payload = {
        "model": "qwen2-7b",
        "messages": messages,
        "temperature": temperature,
        "top_p": 1,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        f"{LLM_BASE_URL}/v1/chat/completions",
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(f"LLM error: {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()
