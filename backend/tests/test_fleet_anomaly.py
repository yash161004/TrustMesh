from datetime import datetime, timezone

import pytest
import pytest_asyncio
from app.main import app
from app.auth.dependencies import get_current_user
from app.db import User, SessionRecord, AgentReputationRecord


_MOCK_ORG1_USER = User(id="org1_user", org_id="org_1", role="standard")
_MOCK_ORG2_USER = User(id="org2_user", org_id="org_2", role="standard")
_MOCK_ORG3_USER = User(id="org3_user", org_id="org_3", role="standard")
_MOCK_NOORG_USER = User(id="noorg_user", org_id=None, role="standard")


@pytest_asyncio.fixture(autouse=True)
async def seed_fleet_data(init_test_db):
    from app.db import get_session_factory
    factory = get_session_factory()
    async with factory() as db:
        now = datetime.now(timezone.utc)

        sessions = [
            SessionRecord(
                id="org1_s_a1", buyer_agent_id="a1", seller_agent_id="dummy",
                status="COMPLETED", outcome="DEAL", org_id="org_1", created_at=now,
            ),
            SessionRecord(
                id="org1_s_a2", buyer_agent_id="a2", seller_agent_id="dummy",
                status="COMPLETED", outcome="DEAL", org_id="org_1", created_at=now,
            ),
            SessionRecord(
                id="org1_s_a3", buyer_agent_id="a3", seller_agent_id="dummy",
                status="COMPLETED", outcome="DEAL", org_id="org_1", created_at=now,
            ),
            SessionRecord(
                id="org1_s_a4", buyer_agent_id="a4", seller_agent_id="dummy",
                status="COMPLETED", outcome="DEAL", org_id="org_1", created_at=now,
            ),
            SessionRecord(
                id="org1_s_a5", buyer_agent_id="a5", seller_agent_id="dummy",
                status="COMPLETED", outcome="DEAL", org_id="org_1", created_at=now,
            ),
            SessionRecord(
                id="org1_s_a6", buyer_agent_id="a6", seller_agent_id="dummy",
                status="COMPLETED", outcome="DEAL", org_id="org_1", created_at=now,
            ),
            SessionRecord(
                id="org2_s_b1", buyer_agent_id="b1", seller_agent_id="b1",
                status="COMPLETED", outcome="DEAL", org_id="org_2", created_at=now,
            ),
            SessionRecord(
                id="org2_s_b2", buyer_agent_id="b2", seller_agent_id="b1",
                status="COMPLETED", outcome="DEAL", org_id="org_2", created_at=now,
            ),
            SessionRecord(
                id="org3_s_c1", buyer_agent_id="c1", seller_agent_id="c1",
                status="COMPLETED", outcome="DEAL", org_id="org_3", created_at=now,
            ),
        ]
        db.add_all(sessions)
        await db.commit()

        reps = [
            AgentReputationRecord(
                agent_id="a1", trust_score=85.0, total_sessions=10,
                violations_count=0, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="a2", trust_score=82.0, total_sessions=10,
                violations_count=0, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="a3", trust_score=90.0, total_sessions=10,
                violations_count=0, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="a4", trust_score=88.0, total_sessions=10,
                violations_count=0, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="a5", trust_score=81.0, total_sessions=10,
                violations_count=0, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="a6", trust_score=30.0, total_sessions=5,
                violations_count=20, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="b1", trust_score=75.0, total_sessions=8,
                violations_count=2, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="b2", trust_score=70.0, total_sessions=10,
                violations_count=3, last_updated=now,
            ),
            AgentReputationRecord(
                agent_id="c1", trust_score=90.0, total_sessions=15,
                violations_count=1, last_updated=now,
            ),
        ]
        db.add_all(reps)
        await db.commit()


@pytest.mark.asyncio
async def test_outlier_detection(test_client):
    app.dependency_overrides[get_current_user] = lambda: _MOCK_ORG1_USER

    resp = test_client.get("/api/v1/fleet/anomalies")
    assert resp.status_code == 200
    data = resp.json()

    assert data["note"] is None
    agents = {a["agent_id"]: a for a in data["agents"]}

    assert agents["a6"]["is_anomalous"] is True
    assert agents["a6"]["z_score"] is not None

    for aid in ("a1", "a2", "a3", "a4", "a5"):
        assert agents[aid]["is_anomalous"] is False
        assert agents[aid]["z_score"] is not None

    assert agents["a1"]["total_sessions"] == 10
    assert agents["a1"]["violations_count"] == 0
    assert agents["a1"]["violation_rate"] == 0.0
    assert agents["a1"]["average_trust_score"] == 85.0

    assert agents["a6"]["violations_count"] == 20
    assert agents["a6"]["total_sessions"] == 5
    assert agents["a6"]["violation_rate"] == 4.0
    assert agents["a6"]["average_trust_score"] == 30.0


@pytest.mark.asyncio
async def test_cross_org_isolation(test_client):
    app.dependency_overrides[get_current_user] = lambda: _MOCK_ORG2_USER

    resp = test_client.get("/api/v1/fleet/anomalies")
    assert resp.status_code == 200
    data = resp.json()

    agent_ids = [a["agent_id"] for a in data["agents"]]
    assert "a1" not in agent_ids
    assert "a6" not in agent_ids
    assert "b1" in agent_ids
    assert "b2" in agent_ids
    assert len(agent_ids) == 2

    assert data["note"] is not None
    for a in data["agents"]:
        assert a["is_anomalous"] is None


@pytest.mark.asyncio
async def test_few_agents_edge_case(test_client):
    app.dependency_overrides[get_current_user] = lambda: _MOCK_ORG3_USER

    resp = test_client.get("/api/v1/fleet/anomalies")
    assert resp.status_code == 200
    data = resp.json()

    assert data["note"] is not None
    assert len(data["agents"]) == 1
    assert data["agents"][0]["is_anomalous"] is None
    assert data["agents"][0]["agent_id"] == "c1"


@pytest.mark.asyncio
async def test_no_org_forbidden(test_client):
    app.dependency_overrides[get_current_user] = lambda: _MOCK_NOORG_USER

    resp = test_client.get("/api/v1/fleet/anomalies")
    assert resp.status_code == 403
