import os
import pytest
from app.auth.dependencies import get_current_user, _auth_enforced
from app.db import User
from app.main import app

@pytest.fixture(autouse=True)
def _ensure_auth_enforced():
    os.environ["AUTH_ENFORCED"] = "true"
    yield

def test_unauthenticated_request_returns_401(test_client):
    assert _auth_enforced() is True
    response = test_client.get("/api/v1/sessions")
    assert response.status_code == 401

def test_invalid_token_returns_401(test_client):
    assert _auth_enforced() is True
    response = test_client.get(
        "/api/v1/sessions",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401

def test_health_endpoint_no_auth_required(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
