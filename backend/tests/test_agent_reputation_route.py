import pytest
from datetime import datetime, timezone
from fastapi import Request
from app.main import app as fastapi_app
from app.auth.dependencies import get_current_user
from app.db import User, AgentReputationRecord, get_session_factory
from app.identity.agent_card import generate_agent_card


@pytest.mark.asyncio
async def test_get_agent_reputation_happy_path(test_client):
    """Happy path: member user fetches reputation for an agent in their own org."""
    agent_id = "test-agent-rep-001"
    org_id = "org-alpha-100"
    
    # 1. Provision AgentCard with org_id
    generate_agent_card(
        role="buyer",
        agent_id=agent_id,
        display_name="Rep Buyer",
        org_id=org_id,
        owner_user_id="user-100",
    )

    # 2. Seed AgentReputationRecord in DB
    factory = get_session_factory()
    async with factory() as db:
        now = datetime.now(timezone.utc)
        record = AgentReputationRecord(
            agent_id=agent_id,
            trust_score=0.85,
            total_sessions=5,
            violations_count=1,
            last_updated=now,
        )
        await db.merge(record)
        await db.commit()

    # 3. Override auth for member user of org-alpha-100
    def user_alpha(request: Request):
        user = User(id="user-100", role="member", org_id=org_id)
        request.state.user = user
        return user

    fastapi_app.dependency_overrides[get_current_user] = user_alpha

    try:
        resp = test_client.get(f"/api/v1/agents/{agent_id}/reputation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == agent_id
        assert data["trust_score"] == 0.85
        assert data["total_sessions"] == 5
        assert data["violations_count"] == 1
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_agent_reputation_org_mismatch_denied(test_client):
    """Org-mismatch denial: non-admin user from another org is denied 403."""
    agent_id = "test-agent-rep-002"
    agent_org_id = "org-alpha-200"
    
    generate_agent_card(
        role="seller",
        agent_id=agent_id,
        display_name="Seller Alpha",
        org_id=agent_org_id,
    )

    # User belongs to org-beta-200 (not org-alpha-200), role member
    def user_beta(request: Request):
        user = User(id="user-200", role="member", org_id="org-beta-200")
        request.state.user = user
        return user

    fastapi_app.dependency_overrides[get_current_user] = user_beta

    try:
        resp = test_client.get(f"/api/v1/agents/{agent_id}/reputation")
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_agent_reputation_admin_cross_org_allowed(test_client):
    """Admin cross-org view: admin user from any org can view agent reputation."""
    agent_id = "test-agent-rep-003"
    agent_org_id = "org-alpha-300"

    generate_agent_card(
        role="buyer",
        agent_id=agent_id,
        display_name="Buyer Alpha",
        org_id=agent_org_id,
    )

    factory = get_session_factory()
    async with factory() as db:
        now = datetime.now(timezone.utc)
        record = AgentReputationRecord(
            agent_id=agent_id,
            trust_score=0.92,
            total_sessions=12,
            violations_count=0,
            last_updated=now,
        )
        await db.merge(record)
        await db.commit()

    # User belongs to org-beta-300, but has role="admin"
    def admin_user(request: Request):
        user = User(id="admin-300", role="admin", org_id="org-beta-300")
        request.state.user = user
        return user

    fastapi_app.dependency_overrides[get_current_user] = admin_user

    try:
        resp = test_client.get(f"/api/v1/agents/{agent_id}/reputation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == agent_id
        assert data["trust_score"] == 0.92
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_agent_reputation_unknown_agent_404(test_client):
    """Unknown agent: returns 404 Not Found if AgentCard does not exist."""
    def any_user(request: Request):
        user = User(id="user-400", role="member", org_id="org-400")
        request.state.user = user
        return user

    fastapi_app.dependency_overrides[get_current_user] = any_user

    try:
        resp = test_client.get("/api/v1/agents/nonexistent-agent-99999/reputation")
        assert resp.status_code == 404
        assert "Agent card not found" in resp.json()["detail"]
    finally:
        fastapi_app.dependency_overrides.clear()
