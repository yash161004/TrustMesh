"""
TrustMesh Ledger Tamper Alerting System.

Sends structured webhook notifications when hash-chain corruption or ledger
tampering is detected during write-time checks or periodic integrity sweeps.
Uses persistent DB-level state (tamper_alerted_at on SessionRecord) backed by an
in-memory cache so alerts survive server restarts, redeploys, and sweep jobs.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional
import httpx

from app.db import claim_tamper_alert

logger = logging.getLogger(__name__)

# Fallback in-memory cache for fast checks and unit tests
_ALERTED_SESSIONS: set[str] = set()


async def trigger_tamper_alert(
    session_id: str,
    org_id: Optional[str] = None,
    broken_at: Optional[int] = None,
    reason: str = "write_time_tamper_check",
) -> bool:
    """
    Send a tamper alert webhook if TAMPER_ALERT_WEBHOOK_URL is configured.
    Atomically claims alert ownership in the DB (UPDATE ... WHERE tamper_alerted_at IS NULL)
    so even under high-concurrency races between web workers and cron sweeps, exactly ONE webhook is sent.
    """
    # 1. Fast in-memory check to bypass DB round-trip if process already knows
    if session_id in _ALERTED_SESSIONS:
        logger.debug("Tamper alert for session %s already sent (in-memory). Skipping duplicate.", session_id)
        return False

    # 2. Atomic DB claim (UPDATE ... WHERE tamper_alerted_at IS NULL)
    claimed = False
    try:
        claimed = await claim_tamper_alert(session_id)
    except Exception as e:
        logger.warning("Could not claim tamper alert status in DB for session %s: %s", session_id, e)
        # Fail-open design decision: If a DB hiccup/outage occurs during tamper detection,
        # we prefer risking a duplicate webhook over failing to dispatch a security alert.
        if session_id in _ALERTED_SESSIONS:
            return False
        claimed = True

    if not claimed:
        _ALERTED_SESSIONS.add(session_id)
        logger.debug("Tamper alert for session %s was already claimed in DB. Skipping duplicate.", session_id)
        return False

    _ALERTED_SESSIONS.add(session_id)

    webhook_url = os.environ.get("TAMPER_ALERT_WEBHOOK_URL")
    payload = {
        "event": "LEDGER_TAMPER_DETECTED",
        "session_id": session_id,
        "org_id": org_id,
        "broken_at": broken_at,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.error(
        "CRITICAL: Ledger tamper detected for session %s (org_id=%s, broken_at=%s, reason=%s)",
        session_id, org_id, broken_at, reason
    )

    if not webhook_url:
        logger.info("TAMPER_ALERT_WEBHOOK_URL not set; logged tamper alert locally without sending HTTP request.")
        return True

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 400:
                logger.warning("Tamper alert webhook returned non-success status %d: %s", resp.status_code, resp.text)
            else:
                logger.info("Tamper alert successfully dispatched to webhook for session %s", session_id)
            return True
    except Exception as e:
        logger.warning("Failed to dispatch tamper alert webhook for session %s: %s", session_id, e)
        return False


def clear_alerted_sessions_cache():
    """Utility function to reset the in-memory deduplication cache (used primarily in tests)."""
    _ALERTED_SESSIONS.clear()

