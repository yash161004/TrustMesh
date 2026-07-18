import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user
from app.db import User
from fastapi import Request

def dummy_user(request: Request = None):
    user = User(id="test-user-1", role="standard", org_id="test-org-1")
    if request:
        request.state.user = user
    return user

@pytest.fixture(autouse=True)
def mock_auth():
    app.dependency_overrides[get_current_user] = dummy_user
    yield
    app.dependency_overrides.clear()

def test_rate_limit_session_create(test_client):
    """Test that hitting POST /sessions 21 times returns 429 on the 21st request."""
    # Reset the limiter so previous tests don't cause early 429s
    app.state.limiter.reset()

    # We send 20 requests that should succeed
    for _ in range(20):
        resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
    # The 21st request should be rate limited
    resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
    assert resp.status_code == 429
    assert "retry-after" in resp.headers

def test_rate_limit_turn(test_client):
    """Test that hitting POST /sessions/{id}/turn 101 times returns 429."""
    app.state.limiter.reset() # clear limits for the test

    resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    for _ in range(100):
        resp = test_client.post(f"/api/v1/sessions/{session_id}/turn", json={"offer": 100})
        assert resp.status_code == 202

    resp = test_client.post(f"/api/v1/sessions/{session_id}/turn", json={"offer": 100})
    assert resp.status_code == 429
    assert "retry-after" in resp.headers
