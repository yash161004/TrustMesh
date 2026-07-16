import pytest
from datetime import datetime, timezone
from app.db import AgentIdentityRecord
import app.db

@pytest.mark.asyncio
async def test_identity_routes(test_client):
    # Insert a test identity directly into the DB
    async with app.db._async_session_factory() as db:
        now = datetime.now(timezone.utc)
        identity = AgentIdentityRecord(
            id="test-buyer-1",
            role="BUYER",
            name="Test Buyer",
            reputation_score=75.5,
            session_count=2,
            created_at=now,
            updated_at=now,
        )
        db.add(identity)
        await db.commit()

    # Test listing identities
    resp = test_client.get("/api/v1/identities")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    found = next((x for x in data if x["id"] == "test-buyer-1"), None)
    assert found is not None
    assert found["role"] == "BUYER"
    assert found["reputation_score"] == 75.5
    assert found["session_count"] == 2

    # Test fetching single identity
    resp = test_client.get("/api/v1/identities/test-buyer-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test-buyer-1"
    assert data["name"] == "Test Buyer"

    # Test fetching nonexistent identity returns 404 (not 500)
    resp = test_client.get("/api/v1/identities/nonexistent-123")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Identity not found"

def test_session_creation_identity_persistence(test_client):
    # Create with explicit identity IDs
    resp = test_client.post("/api/v1/sessions", json={
        "provider": "mock",
        "buyer_identity_id": "test-custom-buyer",
        "seller_identity_id": "test-custom-seller"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["buyer_identity_id"] == "test-custom-buyer"
    assert data["seller_identity_id"] == "test-custom-seller"

    # Create without explicit identity IDs
    # Pydantic applies default values defined in CreateSessionRequest
    resp = test_client.post("/api/v1/sessions", json={
        "provider": "mock"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["buyer_identity_id"] is None
    assert data["seller_identity_id"] is None

    # Create with explicit null identity IDs
    # Tests if null is accepted and overrides defaults
    resp = test_client.post("/api/v1/sessions", json={
        "provider": "mock",
        "buyer_identity_id": None,
        "seller_identity_id": None
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["buyer_identity_id"] is None
    assert data["seller_identity_id"] is None
