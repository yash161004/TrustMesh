import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user, User
from app.models import NegotiationSessionStatus

# Mock Users
user_a = User(id="user_a", clerk_user_id="clerk_a", email="a@org1.test", role="standard", org_id="org_1")
user_b = User(id="user_b", clerk_user_id="clerk_b", email="b@org1.test", role="standard", org_id="org_1")
user_c = User(id="user_c", clerk_user_id="clerk_c", email="c@org2.test", role="standard", org_id="org_2")

def test_tenant_visibility():
    client = TestClient(app)

    # 1. Test Unauthenticated Access to /trust and /ledger
    # We clear dependency overrides to test default auth failure
    app.dependency_overrides = {}
    fake_id = "12345678-1234-5678-1234-567812345678"
    
    r_trust = client.get(f"/api/v1/sessions/{fake_id}/trust")
    assert r_trust.status_code == 401, f"Expected 401, got {r_trust.status_code}"
    
    r_ledger = client.get(f"/api/v1/sessions/{fake_id}/ledger")
    assert r_ledger.status_code == 401, f"Expected 401, got {r_ledger.status_code}"

    # 2. Test Org-Shared Visibility
    # Authenticate as User A
    app.dependency_overrides[get_current_user] = lambda: user_a
    r_create = client.post(
        "/api/v1/sessions",
        json={"buyer_agent_id": "b1", "seller_agent_id": "s1"}
    )
    assert r_create.status_code == 200, f"Create failed: {r_create.text}"
    session_id = r_create.json()["session_id"]
    
    # User A can get it
    r_a = client.get(f"/api/v1/sessions/{session_id}")
    assert r_a.status_code == 200

    # User B (same org) can get it
    app.dependency_overrides[get_current_user] = lambda: user_b
    r_b = client.get(f"/api/v1/sessions/{session_id}")
    assert r_b.status_code == 200

    # User C (different org) CANNOT get it
    app.dependency_overrides[get_current_user] = lambda: user_c
    r_c = client.get(f"/api/v1/sessions/{session_id}")
    assert r_c.status_code == 403, f"Expected 403, got {r_c.status_code}"

    # 3. Test WebSocket Org-Shared Visibility
    from app.auth.dependencies import get_current_user_ws
    from fastapi.websockets import WebSocketDisconnect
    
    # User A (same org)
    app.dependency_overrides[get_current_user_ws] = lambda: user_a
    with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
        data = ws.receive_json()
        assert data["type"] == "history"
        
    # User B (same org)
    app.dependency_overrides[get_current_user_ws] = lambda: user_b
    with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
        data = ws.receive_json()
        assert data["type"] == "history"

    # User C (different org) - Should get 403 forbidden
    app.dependency_overrides[get_current_user_ws] = lambda: user_c
    try:
        with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            pass
        assert False, "Should have raised WebSocketDisconnect"
    except WebSocketDisconnect as e:
        assert e.code == 4003

    print("All tests passed! Tenant isolation (REST & WS) is working.")
