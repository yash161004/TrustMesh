import pytest
from httpx import AsyncClient
import time
import json
import base64
import hmac
import hashlib
from unittest.mock import patch

# We use the same svix library logic to generate a valid signature for tests.
def generate_svix_signature(secret: str, msg_id: str, timestamp: str, body: bytes) -> str:
    # svix webhook signature generation:
    # format: `msg_id.timestamp.body`
    to_sign = f"{msg_id}.{timestamp}.{body.decode('utf-8')}".encode('utf-8')
    sig = hmac.new(secret.split("_")[-1].encode('utf-8') if secret.startswith("whsec_") else secret.encode('utf-8'), to_sign, hashlib.sha256).digest()
    return base64.b64encode(sig).decode('utf-8')

@pytest.mark.asyncio
async def test_clerk_webhook_missing_secret(test_client: AsyncClient, monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "clerk_webhook_secret", "")
    
    response = test_client.post("/api/v1/webhooks/clerk", json={"type": "user.created"})
    assert response.status_code == 500
    assert "CLERK_WEBHOOK_SECRET not configured" in response.text

@pytest.mark.asyncio
async def test_clerk_webhook_invalid_signature(test_client, monkeypatch):
    from app.config import get_settings
    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "clerk_webhook_secret", "whsec_testsecret")
    
    headers = {
        "svix-id": "msg_123",
        "svix-timestamp": str(int(time.time())),
        "svix-signature": "v1,invalid_signature"
    }
    response = test_client.post("/api/v1/webhooks/clerk", json={"type": "user.created"}, headers=headers)
    assert response.status_code == 400
    assert "Invalid signature" in response.text

@pytest.mark.asyncio
@patch("app.routes.webhooks.Webhook.verify")
async def test_clerk_webhook_user_created(mock_verify, test_client, monkeypatch):
    from app.config import get_settings
    from app.db import get_session_db, User
    from sqlalchemy import select
    
    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "clerk_webhook_secret", "whsec_testsecret")
    
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_123",
            "email_addresses": [{"email_address": "test@example.com"}]
        }
    }
    
    # Mock the verify to return the payload parsed
    mock_verify.return_value = payload
    
    headers = {
        "svix-id": "msg_123",
        "svix-timestamp": str(int(time.time())),
        "svix-signature": "v1,dummy_sig"
    }
    
    response = test_client.post("/api/v1/webhooks/clerk", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"success": True}
    
    # Verify in DB (using test client's logic - which we can just do by creating a new session from the app's db module)
    # The webhook used the dependency injected DB session. We can use `test_client.app` or similar but since we are async, let's just use the `get_session_db` fixture if possible.
    # We will verify it manually here using the app's async session maker.
    from app.db import get_session_factory
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(User).where(User.clerk_user_id == "user_123"))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == "test@example.com"

@pytest.mark.asyncio
@patch("app.routes.webhooks.Webhook.verify")
async def test_clerk_webhook_org_created(mock_verify, test_client, monkeypatch):
    from app.config import get_settings
    from app.db import get_session_db, Organization, User
    from sqlalchemy import select
    
    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "clerk_webhook_secret", "whsec_testsecret")
    
    # Create the user first
    from app.db import get_session_factory
    factory = get_session_factory()
    async with factory() as db:
        new_user = User(clerk_user_id="user_123", email="test@example.com")
        db.add(new_user)
        await db.commit()
    
    payload = {
        "type": "organization.membership.created",
        "data": {
            "organization": {
                "id": "org_123",
                "name": "Test Org"
            },
            "public_user_data": {
                "user_id": "user_123"
            },
            "role": "org:admin"
        }
    }
    
    mock_verify.return_value = payload
    
    headers = {
        "svix-id": "msg_124",
        "svix-timestamp": str(int(time.time())),
        "svix-signature": "v1,dummy_sig"
    }
    
    response = test_client.post("/api/v1/webhooks/clerk", json=payload, headers=headers)
    assert response.status_code == 200
    
    from app.db import get_session_factory
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(Organization).where(Organization.clerk_org_id == "org_123"))
        org = result.scalar_one_or_none()
        assert org is not None
        assert org.name == "Test Org"
        
        # Verify user org_id was updated and role was set to admin
        result = await db.execute(select(User).where(User.clerk_user_id == "user_123"))
        user = result.scalar_one_or_none()
        assert user.org_id == org.id
        assert user.role == "admin"
