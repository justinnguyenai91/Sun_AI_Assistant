import pytest
from fastapi.testclient import TestClient
from app.app import app

client = TestClient(app)

def test_analyze_integration():
    headers = {"Authorization": "Bearer dev-key-123"}
    resp = client.post("/analyze", json={"input": "Hay thống kê sản lượng 1 năm qua theo line"}, headers=headers)
    assert resp.status_code == 200, resp.text
    j = resp.json()

    # Basic shape
    assert "user_input" in j
    assert "intent" in j
    assert "planner_result" in j

    # Intent checks
    intent = j["intent"]
    assert isinstance(intent, dict)
    assert intent.get("intent") == "report"

    # Planner result checks
    pr = j["planner_result"]
    assert isinstance(pr, dict)
    assert "data" in pr and isinstance(pr["data"], list)
    assert pr.get("count") == len(pr["data"])

    # Decision (planner response) should be present and contain data as well
    decision = j.get("decision")
    assert isinstance(decision, dict)
    assert "data" in decision
