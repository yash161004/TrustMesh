import pytest
from app.main import app

def test_health_endpoint(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_session_endpoints(test_client):
    # Create
    resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    assert session_id

    # Start
    start_resp = test_client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_resp.status_code == 200

    # Turn
    turn_resp = test_client.post(f"/api/v1/sessions/{session_id}/turn", json={"max_turns": 1})
    assert turn_resp.status_code == 200

    # List messages
    msgs_resp = test_client.get(f"/api/v1/sessions/{session_id}/messages")
    assert msgs_resp.status_code == 200
    assert len(msgs_resp.json()) > 0
