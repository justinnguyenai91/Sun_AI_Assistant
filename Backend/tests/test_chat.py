from fastapi.testclient import TestClient
from app import app
client = TestClient(app)

def test_chat_with_auth(monkeypatch):
    # mock adapter cho nhanh: trả data OpenAI-ish
    def fake_chat(payload): return {"status":200, "data":{
        "id":"chatcmpl-test","object":"chat.completion","created":0,"model":payload["model"],
        "choices":[{"index":0,"message":{"role":"assistant","content":"pong"},"finish_reason":"stop"}],
        "usage":{"prompt_tokens":None,"completion_tokens":None,"total_tokens":None}
    }}
    from adapters import llama_client
    monkeypatch.setattr(llama_client, "chat", lambda p: fake_chat(p))

    r = client.post("/v1/chat/completions",
        headers={"Authorization":"Bearer dev-key-123"},
        json={"model":"qwen2-7b","messages":[{"role":"user","content":"ping"}]}
    )
    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["content"] == "pong"
