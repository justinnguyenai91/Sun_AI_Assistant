from fastapi.testclient import TestClient
from app import app
client = TestClient(app)

def test_health():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
