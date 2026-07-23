import pytest
from datetime import datetime, timezone
from app.db import AgentIdentityRecord
import app.db

@pytest.mark.asyncio
async def test_identity_routes(test_client):
    # The identity routes are org-tenancy scoped and require auth; list as an
    # admin so we see the seeded/inserted identity regardless of org binding.
    from app.main import app as fastapi_app
    from app.auth.dependencies import get_current_user
    from app.db import User

    def _admin_user():
        return User(id="test-admin", role="admin", org_id=None)

    fastapi_app.dependency_overrides[get_current_user] = _admin_user
    try:
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
    finally:
        fastapi_app.dependency_overrides.pop(get_current_user, None)

from app.main import app as fastapi_app
from app.auth.dependencies import get_current_user
from app.db import User

from fastapi import Request

def dummy_user(request: Request):
    user = User(id="test-user-1", role="standard", org_id="test-org-1")
    request.state.user = user
    return user

def test_session_creation_identity_persistence(test_client):
    fastapi_app.dependency_overrides[get_current_user] = dummy_user
    try:
        # Explicit identity IDs are preserved as-is.
        resp = test_client.post("/api/v1/sessions", json={
            "provider": "mock",
            "buyer_identity_id": "test-custom-buyer",
            "seller_identity_id": "test-custom-seller"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["buyer_identity_id"] == "test-custom-buyer"
        assert data["seller_identity_id"] == "test-custom-seller"

        # Without explicit IDs, org-scoped identities are auto-provisioned
        # (per Phase 1 identity hardening) — no longer left None.
        resp = test_client.post("/api/v1/sessions", json={
            "provider": "mock"
        })
        assert resp.status_code == 200
        data = resp.json()
        auto_buyer = data["buyer_identity_id"]
        auto_seller = data["seller_identity_id"]
        assert auto_buyer is not None
        assert auto_seller is not None
        assert auto_buyer != auto_seller  # buyer and seller are distinct identities

        # Explicit null is treated the same as omitted: auto-provisioned, and
        # idempotent per (org, role) — the same org resolves the same identity.
        resp = test_client.post("/api/v1/sessions", json={
            "provider": "mock",
            "buyer_identity_id": None,
            "seller_identity_id": None
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["buyer_identity_id"] == auto_buyer
        assert data["seller_identity_id"] == auto_seller
    finally:
        fastapi_app.dependency_overrides.pop(get_current_user, None)
