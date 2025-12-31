from fastapi.testclient import TestClient
from app import app
client = TestClient(app)

def test_chat_no_auth():
    r = client.post("/v1/chat/completions", json={"model":"x","messages":[{"role":"user","content":"hi"}]})
    assert r.status_code == 401
