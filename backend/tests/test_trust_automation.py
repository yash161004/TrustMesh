import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_session_factory, TrustReportRecord
from sqlalchemy import select

client = TestClient(app)

# We will test the automation of trust evaluation.
# We create a session, start it, and force it to complete by accepting the first offer.
# Then we verify the trust report was automatically generated.

@pytest.mark.asyncio
async def test_trust_evaluated_automatically_on_completion():
    # 1. Create a session
    payload = {
        "buyer_agent_id": "buyer-agent-001",
        "seller_agent_id": "seller-agent-001",
        "buyer_identity_id": "buyer-ident-001",
        "seller_identity_id": "seller-ident-001",
        # Use the mock provider: this test covers trust-report automation, not
        # live inference. Without it the request defaults to gemini and fails in
        # CI with "Cannot create real session: GEMINI_API_KEY is missing".
        "provider": "mock",
    }
    
    from app.auth.dependencies import get_current_user
    from app.db import User
    
    async def mock_get_current_user():
        return User(id="test-user-id", role="admin", email="test@test.com", org_id="test-org")
        
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    headers = {}
    
    response = client.post("/api/v1/sessions", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    session_id = response.json()["session_id"]
    
    # 2. Start session
    response = client.post(f"/api/v1/sessions/{session_id}/start", headers=headers)
    assert response.status_code == 202, response.text
    
    # 3. Seller rejects, Buyer accepts (to force completion quickly)
    from unittest.mock import patch, AsyncMock
    with patch("app.trust.detectors.manipulation.ManipulationDetector.evaluate", new_callable=AsyncMock) as mock_manipulation, \
         patch("app.trust.detectors.commitments.CommitmentConsistencyChecker.evaluate", new_callable=AsyncMock) as mock_commitment:
        mock_manipulation.return_value = {"flagged": False, "trust_impact": 0, "reason": "mocked", "status": "CLEARED"}
        mock_commitment.return_value = {"flagged": False, "trust_impact": 0, "reason": "mocked", "status": "CLEARED"}
        
        for i in range(5):
            turn_response = client.post(f"/api/v1/sessions/{session_id}/turn", json={"max_turns": 2}, headers=headers)
            assert turn_response.status_code == 202, turn_response.text
            
            # Check if completed
            get_response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
            if get_response.json()["status"] == "COMPLETED":
                break
                
    # Check it actually completed
    get_response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert get_response.json()["status"] == "COMPLETED", "Session did not complete in mock."
    
    # 4. Assert TrustReportRecord exists in DB!
    # BackgroundTasks run synchronously in FastAPI TestClient upon response, but we wait just in case
    import asyncio
    await asyncio.sleep(0.1)
    
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(TrustReportRecord).where(TrustReportRecord.session_id == session_id))
        report = result.scalar_one_or_none()
        
    assert report is not None, "TrustReportRecord was not generated automatically!"
    assert report.session_id == session_id
    
    # restore override
    app.dependency_overrides.clear()
