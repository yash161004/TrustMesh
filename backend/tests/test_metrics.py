import json
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from app.main import app
from app.auth.dependencies import get_current_user
from app.db import User, SessionRecord, TrustReportRecord


def dummy_admin(request=None):
    user = User(id="admin", role="admin", org_id="test-org")
    if request is not None:
        request.state.user = user
    return user


@pytest.fixture(autouse=True)
def mock_admin():
    app.dependency_overrides[get_current_user] = dummy_admin
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def seed_data(init_test_db):
    from app.db import get_session_factory, save_ledger_entry
    factory = get_session_factory()
    async with factory() as db:
        now = datetime.now(timezone.utc)
        sessions = [
            SessionRecord(
                id="s1", buyer_agent_id="b1", seller_agent_id="s1",
                status="COMPLETED", outcome="DEAL", data_source="real_llm_v1",
                org_id="org-a", created_at=now,
            ),
            SessionRecord(
                id="s2", buyer_agent_id="b2", seller_agent_id="s2",
                status="COMPLETED", outcome="NO_DEAL", data_source="real_llm_v1",
                org_id="org-a", created_at=now,
            ),
            SessionRecord(
                id="s3", buyer_agent_id="b3", seller_agent_id="s3",
                status="COMPLETED", outcome="FAILED", data_source="real_llm_v1",
                org_id="org-b", created_at=now,
            ),
            SessionRecord(
                id="s4", buyer_agent_id="b4", seller_agent_id="s4",
                status="COMPLETED", outcome="DEAL", data_source="real_llm_v1",
                org_id="org-b", created_at=now,
                tamper_alerted_at=now,
            ),
        ]
        db.add_all(sessions)
        await db.commit()

        trust_reports = [
            TrustReportRecord(
                session_id="s1",
                report_json=json.dumps({
                    "violations": [
                        {"violation_type": "MANIPULATION_PATTERN", "severity": "HIGH"},
                        {"violation_type": "POLICY_VIOLATION", "severity": "LOW"},
                    ],
                    "buyer_score": {"overall_score": 80.0},
                    "seller_score": {"overall_score": 90.0},
                }),
                evaluated_at=now,
                created_at=now,
            ),
            TrustReportRecord(
                session_id="s2",
                report_json=json.dumps({
                    "violations": [
                        {"violation_type": "MANIPULATION_PATTERN", "severity": "CRITICAL"},
                    ],
                    "buyer_score": {"overall_score": 50.0},
                    "seller_score": {"overall_score": 60.0},
                }),
                evaluated_at=now,
                created_at=now,
            ),
        ]
        db.add_all(trust_reports)
        await db.commit()

        await save_ledger_entry(
            session_id="s1", sequence=1,
            message_json='{"msg":"hello"}',
            signature="sig1", signer_public_key="pk1",
            prev_hash="0" * 64, entry_hash="a" * 64,
            created_at=now,
        )
        await save_ledger_entry(
            session_id="s1", sequence=2,
            message_json='{"msg":"world"}',
            signature="sig2", signer_public_key="pk1",
            prev_hash="a" * 64, entry_hash="b" * 64,
            created_at=now,
        )


@pytest.mark.asyncio
async def test_metrics_shape(test_client):
    resp = test_client.get("/api/v1/metrics/")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_sessions"] == 4
    assert data["sessions_by_outcome"] == {"DEAL": 2, "NO_DEAL": 1, "FAILED": 1}
    assert data["violations_by_severity"] == {"HIGH": 1, "LOW": 1, "CRITICAL": 1}
    assert data["violations_by_type"] == {"MANIPULATION_PATTERN": 2, "POLICY_VIOLATION": 1}
    assert data["tamper_alerts_fired"] == 1
    assert data["total_ledger_entries"] == 2


@pytest.mark.asyncio
async def test_metrics_rejects_non_admin(test_client):
    from app.auth.dependencies import get_current_user
    def dummy_standard(request=None):
        user = User(id="user", role="standard", org_id="org-a")
        if request is not None:
            request.state.user = user
        return user
    app.dependency_overrides[get_current_user] = dummy_standard
    resp = test_client.get("/api/v1/metrics/")
    assert resp.status_code == 403
