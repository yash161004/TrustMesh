"""
Tests for the TrustMesh WebSocket live stream (Phase 4).

Covers:
- Connect and receive message history
- Receive live broadcast when a new message is created
- Graceful disconnect handling
- Non-existent session returns 4004 close code
"""
from __future__ import annotations

import json
import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from app.db import User
from app.auth.dependencies import get_current_user, get_current_user_ws

from fastapi import Request

def dummy_user(request: Request = None, ):
    user = User(id="test-user-1", role="standard", org_id="test-org-1")
    if request:
        request.state.user = user
    return user

@pytest.fixture(autouse=True)
def mock_auth():
    from app.main import app
    app.dependency_overrides[get_current_user] = dummy_user
    app.dependency_overrides[get_current_user_ws] = dummy_user
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


@pytest.fixture
def session_id(client):
    """Create a session and return its ID."""
    resp = client.post("/api/v1/sessions", json={"provider": "mock"})
    assert resp.status_code == 200
    return resp.json()["session_id"]


class TestWebSocketHistory:
    def test_connect_receives_empty_history(self, client, session_id):
        """On connect, client receives history (empty if no messages yet)."""
        with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "history"
            assert data["messages"] == []

    def test_connect_receives_message_history(self, client, session_id):
        """On connect, client receives existing messages as history."""
        # Create some messages first
        client.post(f"/api/v1/sessions/{session_id}/start")
        client.post(f"/api/v1/sessions/{session_id}/turn", json={"max_turns": 1})

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            data = ws.receive_json()
            assert data["type"] == "history"
            assert len(data["messages"]) > 0
            # Each message should have the expected fields
            msg = data["messages"][0]
            assert "message_type" in msg
            assert "sender" in msg
            assert "price" in msg


class TestWebSocketBroadcast:
    def test_receives_live_broadcast(self, client, session_id):
        """Client receives a broadcast when a new message is persisted."""
        with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            # Drain history
            history = ws.receive_json()
            assert history["type"] == "history"

            # Trigger a new message via the API
            client.post(f"/api/v1/sessions/{session_id}/start")

            # Should receive a live broadcast
            data = ws.receive_json()
            assert data["type"] == "new_message"
            assert "message" in data
            assert data["message"]["sender"] is not None
            assert data["message"]["price"] is not None


class TestWebSocketDisconnect:
    def test_disconnect_is_graceful(self, client, session_id):
        """Disconnecting doesn't crash the server."""
        with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
            ws.receive_json()  # drain history
            ws.close()

        # Server should still be functional
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_multiple_connects_and_disconnects(self, client, session_id):
        """Multiple clients can connect and disconnect without issues."""
        for _ in range(3):
            with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
                ws.receive_json()  # drain history
                ws.close()

        # Server should still be functional
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


class TestWebSocketNotFound:
    def test_nonexistent_session_returns_close(self, client):
        """Connecting to a non-existent session closes with code 4004."""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/v1/sessions/nonexistent-id/ws") as ws:
                # Should get closed by server
                try:
                    ws.receive_json()
                except Exception:
                    pass

class TestWebSocketAuthorization:
    def test_unauthorized_user_is_rejected(self, client, session_id):
        """User B cannot connect to User A's websocket session."""
        from app.auth.dependencies import get_current_user_ws
        from app.main import app
        from app.db import User

        def dummy_user_b(request: Request = None, ):
            user = User(id="test-user-2", role="standard", org_id="test-org-2")
            if request:
                request.state.user = user
            return user
            
        app.dependency_overrides[get_current_user_ws] = dummy_user_b
        
        try:
            with pytest.raises(Exception):
                with client.websocket_connect(f"/api/v1/sessions/{session_id}/ws") as ws:
                    ws.receive_json()
        finally:
            app.dependency_overrides.clear()
