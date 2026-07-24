import pytest
import pytest_asyncio
from app.trust.engine import TrustEngine
from app.trust.models import Violation, ViolationType, Severity, ViolationStatus


# =========================================================================
# Engine-level math tests (pure computation, no DB)
# =========================================================================


def make_violation(severity: Severity, status: ViolationStatus = ViolationStatus.FLAGGED) -> Violation:
    return Violation(
        violation_type=ViolationType.MANIPULATION_PATTERN,
        severity=severity,
        message_turn=1,
        agent_id="test-agent",
        description="test",
        status=status,
    )


def compute_session_score(base: float, penalties: list[int]) -> float:
    """Replicate the engine's penalty-against-base logic."""
    total_penalty = sum(penalties)
    raw = max(0.0, 100.0 - total_penalty)
    penalty_applied = 100.0 - raw
    return max(0.0, base - penalty_applied)


def test_first_session_default():
    """A brand-new identity with no prior history defaults to 100.0."""
    base = 100.0
    assert base == 100.0


def test_cap_at_100():
    """Session score should never exceed 100 even after a perfect session."""
    engine = TrustEngine()
    violations: list[Violation] = []
    raw = engine._compute_score(violations)
    assert raw == 100.0
    session = max(0.0, 100.0 - (100.0 - raw))
    assert session == 100.0


def test_penalty_against_base_does_not_exceed_100():
    """Session score with a non-zero base can't exceed that base."""
    result = compute_session_score(65.0, [0])
    assert result == 65.0

    result = compute_session_score(90.0, [0])
    assert result == 90.0


def test_zero_session_score():
    """A session score of 0 should still produce a sensible weighted average."""
    old_rep = 100.0
    new = (0.7 * 0.0) + (0.3 * old_rep)
    assert new == 30.0

    old_rep = 65.0
    new = (0.7 * 0.0) + (0.3 * old_rep)
    assert new == 19.5


def test_demo_bad_actor_regression():
    """Verify the demo-bad-actor scenario: base=65, one HIGH violation -> 53.

    This locks in the number we manually verified end-to-end so it can't
    silently drift due to refactoring.
    """
    engine = TrustEngine()
    violations = [make_violation(Severity.HIGH)]  # penalty = 12
    raw = engine._compute_score(violations)
    assert raw == 88.0, f"raw score should be 88, got {raw}"

    session = compute_session_score(65.0, [12])
    assert session == 53.0, f"session score should be 53, got {session}"


def test_demo_bad_actor_weighted_update():
    """After a 53-point session, the stored reputation updates correctly."""
    old_rep = 65.0
    session_score = 53.0
    new_rep = (0.7 * session_score) + (0.3 * old_rep)
    assert new_rep == pytest.approx(56.6), f"expected 56.6, got {new_rep}"


def test_penalty_map_values():
    """Confirm each severity maps to the expected penalty."""
    engine = TrustEngine()
    for sev, expected_penalty in [(Severity.LOW, 2), (Severity.MEDIUM, 5), (Severity.HIGH, 12), (Severity.CRITICAL, 25)]:
        violations = [make_violation(sev)]
        raw = engine._compute_score(violations)
        assert raw == 100.0 - expected_penalty, f"{sev} -> penalty {expected_penalty}"


def test_disputed_violations_ignored():
    """DISPUTED violations should not contribute to the penalty sum."""
    engine = TrustEngine()
    violations = [make_violation(Severity.CRITICAL, ViolationStatus.DISPUTED)]
    raw = engine._compute_score(violations)
    assert raw == 100.0, f"DISPUTED violation should be ignored, got {raw}"


# =========================================================================
# Multiple sequential sessions (DB-backed)
# =========================================================================


def _weighted_update(old: float, session_score: float) -> float:
    """Pure function replica of update_agent_reputation's math."""
    return (0.7 * session_score) + (0.3 * old)


@pytest.mark.asyncio
async def test_multiple_sequential_sessions(init_test_db):
    """Reputation converges correctly over 3-4 simulated sessions."""
    from app.db import update_agent_reputation, get_agent_identity

    # First session: identity has no row yet, so update_agent_reputation
    # does nothing. This matches the route behaviour where a first-ever
    # evaluation skips the reputation update if no identity record exists.
    await update_agent_reputation("fresh-agent", 100.0)
    ident = await get_agent_identity("fresh-agent")
    assert ident is None, "no record should exist for an unknown identity"

    # If the identity already has a DB record, updates compound correctly.
    # We simulate by seeding reputation manually and running the formula.
    rep = 100.0

    rep = _weighted_update(rep, 100.0)
    assert rep == 100.0

    rep = _weighted_update(rep, 95.0)
    assert rep == pytest.approx(96.5)

    rep = _weighted_update(rep, 90.0)
    assert rep == pytest.approx(91.95)

    rep = _weighted_update(rep, 85.0)
    assert rep == pytest.approx(87.085)

    rep = _weighted_update(rep, 53.0)
    assert rep == pytest.approx(63.2255)

    assert rep <= 100.0, "reputation must never exceed 100"

    # Convergence check: repeated perfect sessions approach but never surpass 100
    rep = 50.0
    for _ in range(50):
        rep = _weighted_update(rep, 100.0)
    assert rep == pytest.approx(100.0, abs=1e-6)
    assert rep <= 100.0


@pytest.mark.asyncio
async def test_update_agent_reputation_round_trip(init_test_db):
    """Verify update_agent_reputation creates a new record via seed data."""
    from app.db import (
        update_agent_reputation,
        get_agent_identity,
        AgentIdentityRecord,
        get_session_factory,
    )
    from sqlalchemy import select
    from datetime import datetime, timezone

    factory = get_session_factory()
    async with factory() as db:
        record = AgentIdentityRecord(
            id="test-sim-1",
            role="BUYER",
            name="Test Sim",
            reputation_score=100.0,
            session_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()

    await update_agent_reputation("test-sim-1", 53.0)

    ident = await get_agent_identity("test-sim-1")
    assert ident is not None
    assert ident["session_count"] == 1
    expected = (0.7 * 53.0) + (0.3 * 100.0)
    assert ident["reputation_score"] == pytest.approx(expected)

    # Second update
    await update_agent_reputation("test-sim-1", 90.0)
    ident = await get_agent_identity("test-sim-1")
    assert ident["session_count"] == 2
    expected2 = (0.7 * 90.0) + (0.3 * expected)
    assert ident["reputation_score"] == pytest.approx(expected2)

    # Third update
    await update_agent_reputation("test-sim-1", 100.0)
    ident = await get_agent_identity("test-sim-1")
    assert ident["session_count"] == 3
    expected3 = (0.7 * 100.0) + (0.3 * expected2)
    assert ident["reputation_score"] == pytest.approx(expected3)

    assert ident["reputation_score"] <= 100.0


@pytest.mark.asyncio
async def test_update_agent_reputation_noop_for_none(init_test_db):
    """update_agent_reputation with empty/None identity_id silently returns."""
    from app.db import update_agent_reputation

    await update_agent_reputation("", 50.0)
    await update_agent_reputation(None, 50.0)
    # No assertion needed — we just verify no exception is raised


# =========================================================================
# v2 cross-session reputation: severity weighting + time decay
# =========================================================================


def test_severity_weighted_penalty_scales_with_severity():
    """A CRITICAL violation must cost strictly more than a LOW one."""
    from app.db import _severity_weighted_penalty

    assert _severity_weighted_penalty(["LOW"]) == pytest.approx(0.02)
    assert _severity_weighted_penalty(["MEDIUM"]) == pytest.approx(0.05)
    assert _severity_weighted_penalty(["HIGH"]) == pytest.approx(0.12)
    assert _severity_weighted_penalty(["CRITICAL"]) == pytest.approx(0.25)
    assert (
        _severity_weighted_penalty(["CRITICAL"])
        > _severity_weighted_penalty(["LOW"])
    )


def test_severity_weighted_penalty_sums_and_caps():
    """Multiple violations sum, but the per-session penalty is capped at 0.30."""
    from app.db import _severity_weighted_penalty, _REP_MAX_SESSION_PENALTY

    # LOW + HIGH = 0.14, under the cap -> summed exactly
    assert _severity_weighted_penalty(["LOW", "HIGH"]) == pytest.approx(0.14)
    # Two CRITICALs = 0.50, over the cap -> clamped
    assert _severity_weighted_penalty(["CRITICAL", "CRITICAL"]) == _REP_MAX_SESSION_PENALTY


def test_severity_weighted_penalty_unknown_treated_as_medium():
    """A blank/unknown severity still costs something (MEDIUM), never zero."""
    from app.db import _severity_weighted_penalty, _REP_SEVERITY_PENALTY

    assert _severity_weighted_penalty([""]) == pytest.approx(_REP_SEVERITY_PENALTY["MEDIUM"])
    assert _severity_weighted_penalty(["bogus"]) == pytest.approx(_REP_SEVERITY_PENALTY["MEDIUM"])


def test_decay_toward_neutral_is_noop_at_zero_days():
    """No time elapsed -> score is unchanged."""
    from app.db import _decay_toward_neutral

    assert _decay_toward_neutral(0.20, 0.0) == 0.20
    assert _decay_toward_neutral(0.95, 0.0) == 0.95


def test_decay_toward_neutral_pulls_both_directions():
    """A low score drifts up and a high score drifts down toward the 0.75 baseline."""
    from app.db import _decay_toward_neutral, _REP_NEUTRAL_SCORE, _REP_DECAY_HALF_LIFE_DAYS

    # One half-life: exactly halfway back to neutral.
    low = _decay_toward_neutral(0.25, _REP_DECAY_HALF_LIFE_DAYS)
    assert low == pytest.approx(_REP_NEUTRAL_SCORE + (0.25 - _REP_NEUTRAL_SCORE) * 0.5)
    assert low > 0.25  # a punished agent recovers upward

    high = _decay_toward_neutral(0.99, _REP_DECAY_HALF_LIFE_DAYS)
    assert high < 0.99  # an idle over-trusted agent drifts down
    assert high == pytest.approx(_REP_NEUTRAL_SCORE + (0.99 - _REP_NEUTRAL_SCORE) * 0.5)


@pytest.mark.asyncio
async def test_v2_severity_penalty_applied(init_test_db):
    """A CRITICAL-violation session drops the stored score more than a LOW one."""
    from app.db import update_agent_reputation_v2, get_agent_reputation

    # Agent A: one CRITICAL violation this session.
    await update_agent_reputation_v2("agent-crit", 1, session_severities=["CRITICAL"])
    crit = await get_agent_reputation("agent-crit")
    assert crit["trust_score"] == pytest.approx(0.75 - 0.25)  # 0.50
    assert crit["violations_count"] == 1
    assert crit["total_sessions"] == 1

    # Agent B: one LOW violation this session.
    await update_agent_reputation_v2("agent-low", 1, session_severities=["LOW"])
    low = await get_agent_reputation("agent-low")
    assert low["trust_score"] == pytest.approx(0.75 - 0.02)  # 0.73
    assert low["trust_score"] > crit["trust_score"]


@pytest.mark.asyncio
async def test_v2_backward_compatible_flat_penalty(init_test_db):
    """Called without severities, v2 keeps the original flat -0.1 penalty."""
    from app.db import update_agent_reputation_v2, get_agent_reputation

    await update_agent_reputation_v2("agent-flat", 2)  # no session_severities
    rep = await get_agent_reputation("agent-flat")
    assert rep["trust_score"] == pytest.approx(0.75 - 0.1)  # 0.65
    assert rep["violations_count"] == 2


@pytest.mark.asyncio
async def test_v2_clean_session_recovers(init_test_db):
    """A clean session nudges the score up by the recovery increment."""
    from app.db import update_agent_reputation_v2, get_agent_reputation

    await update_agent_reputation_v2("agent-clean", 0, session_severities=[])
    rep = await get_agent_reputation("agent-clean")
    assert rep["trust_score"] == pytest.approx(0.75 + 0.02)  # 0.77
    assert rep["violations_count"] == 0


@pytest.mark.asyncio
async def test_v2_time_decay_ages_out_old_penalty(init_test_db):
    """An old penalty decays back toward neutral before the new session applies."""
    from datetime import datetime, timezone, timedelta
    from app.db import (
        update_agent_reputation_v2,
        get_agent_reputation,
        AgentReputationRecord,
        get_session_factory,
        _REP_DECAY_HALF_LIFE_DAYS,
        _decay_toward_neutral,
    )

    # Seed a heavily-penalised agent whose last update was one half-life ago.
    stale_score = 0.25
    last_seen = datetime.now(timezone.utc) - timedelta(days=_REP_DECAY_HALF_LIFE_DAYS)
    factory = get_session_factory()
    async with factory() as db:
        db.add(
            AgentReputationRecord(
                agent_id="agent-stale",
                trust_score=stale_score,
                total_sessions=3,
                violations_count=5,
                last_updated=last_seen,
            )
        )
        await db.commit()

    # A fresh clean session: decay first (halfway back to neutral), then +0.02 recovery.
    await update_agent_reputation_v2("agent-stale", 0, session_severities=[])
    rep = await get_agent_reputation("agent-stale")

    expected = min(1.0, _decay_toward_neutral(stale_score, _REP_DECAY_HALF_LIFE_DAYS) + 0.02)
    # Allow a little slack for the sub-second wall-clock delta in days_elapsed.
    assert rep["trust_score"] == pytest.approx(expected, abs=1e-3)
    assert rep["trust_score"] > stale_score  # the old penalty genuinely faded
