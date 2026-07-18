import pytest
from app.main import app
from app.auth.dependencies import get_current_user
from app.db import User

from fastapi import Request

def dummy_user_a(request: Request = None, ):
    user = User(id="user-a", role="standard", org_id="org-a")
    if request:
        request.state.user = user
    return user

def dummy_user_b(request: Request = None, ):
    user = User(id="user-b", role="standard", org_id="org-b")
    if request:
        request.state.user = user
    return user

def dummy_admin(request: Request = None, ):
    user = User(id="admin", role="admin", org_id="org-admin")
    if request:
        request.state.user = user
    return user

@pytest.fixture
def mock_user_a():
    app.dependency_overrides[get_current_user] = dummy_user_a
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user_b():
    app.dependency_overrides[get_current_user] = dummy_user_b
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def mock_admin():
    app.dependency_overrides[get_current_user] = dummy_admin
    yield
    app.dependency_overrides.clear()


def test_auth_read_endpoints(test_client, mock_user_a):
    """Test read endpoints properly filter by org and enforce ownership."""
    # User A creates a session
    resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
    assert resp.status_code == 200
    session_id_a = resp.json()["session_id"]
    
    # User A can read it
    resp = test_client.get(f"/api/v1/sessions/{session_id_a}")
    assert resp.status_code == 200
    
    # User A can read messages
    resp = test_client.get(f"/api/v1/sessions/{session_id_a}/messages")
    assert resp.status_code == 200
    
    # Switch to User B
    app.dependency_overrides[get_current_user] = dummy_user_b
    
    # User B CANNOT read User A's session
    resp = test_client.get(f"/api/v1/sessions/{session_id_a}")
    assert resp.status_code == 403
    
    # User B CANNOT read User A's messages
    resp = test_client.get(f"/api/v1/sessions/{session_id_a}/messages")
    assert resp.status_code == 403

def test_auth_write_endpoints(test_client, mock_user_a):
    """Test write endpoints properly enforce ownership."""
    # User A creates a session
    resp = test_client.post("/api/v1/sessions", json={"provider": "mock"})
    assert resp.status_code == 200
    session_id_a = resp.json()["session_id"]
    
    # Switch to User B
    app.dependency_overrides[get_current_user] = dummy_user_b
    
    # User B CANNOT start User A's session (Write endpoint)
    resp = test_client.post(f"/api/v1/sessions/{session_id_a}/start")
    assert resp.status_code == 403 
    
    # User B CANNOT submit a turn on User A's session (Write endpoint)
    resp = test_client.post(f"/api/v1/sessions/{session_id_a}/turn", json={"max_turns": 1})
    assert resp.status_code == 403 

def test_admin_endpoints(test_client, mock_user_a):
    """Test admin endpoints properly enforce admin role."""
    # User A (role: standard) tries to access admin endpoint
    resp = test_client.get("/api/v1/admin/sessions")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Insufficient permissions"
    
    # Mock an admin user
    def dummy_admin_user(request: Request = None, ):
        user = User(id="test-admin-1", role="admin", org_id="admin-org")
        if request:
            request.state.user = user
        return user
        
    app.dependency_overrides[get_current_user] = dummy_admin_user
    
    # Admin user can access
    resp = test_client.get("/api/v1/admin/sessions")
    assert resp.status_code == 200
