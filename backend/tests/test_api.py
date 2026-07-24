import pytest
from app.main import app

def test_health_endpoint(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

from app.auth.dependencies import get_current_user
from app.db import User

from fastapi import Request

def dummy_user(request: Request):
    user = User(id="test-user-1", role="standard", org_id="test-org-1")
    request.state.user = user
    return user

def test_session_endpoints(test_client):
    # NOTE: this override must be torn down. Leaking it makes every later test
    # file (e.g. test_auth_smoke) see an authenticated user and get 200 where a
    # 401 is expected — a real CI-only failure, since this file sorts before them.
    app.dependency_overrides[get_current_user] = dummy_user
    try:
        # Create
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        assert resp.status_code == 200
        data = resp.json()
        session_id = data["session_id"]
        assert session_id

        # Start
        start_resp = test_client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_resp.status_code == 202

        # Turn
        turn_resp = test_client.post(f"/api/v1/sessions/{session_id}/turn", json={"max_turns": 1})
        assert turn_resp.status_code == 202

        # List messages
        msgs_resp = test_client.get(f"/api/v1/sessions/{session_id}/messages")
        assert msgs_resp.status_code == 200
        assert len(msgs_resp.json()) > 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
