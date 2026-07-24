"""Regression test for AgentCard org-scoping.

Verifies that two different organizations can register an agent with the same agent_id
(e.g., 'buyer-0') and that their AgentCards are stored independently in distinct file paths,
neither overwrites the other, and verification for each org only succeeds against its own card.
"""
import pytest
from app.identity.agent_card import (
    generate_agent_card,
    verify_agent_card,
    card_file_path,
    get_or_create_agent_card,
)


def test_agent_card_org_scoping_isolation(tmp_path, monkeypatch):
    """Assert two orgs registering same agent_id persist independently without overwrite."""
    monkeypatch.setenv("AGENT_CARD_DIR", str(tmp_path))

    agent_id = "buyer-0"
    org_alpha = "org-alpha"
    org_beta = "org-beta"

    card_alpha, sig_alpha = generate_agent_card(
        role="buyer",
        agent_id=agent_id,
        display_name="Alpha Buyer 0",
        org_id=org_alpha,
        owner_user_id="user-alpha",
    )

    card_beta, sig_beta = generate_agent_card(
        role="buyer",
        agent_id=agent_id,
        display_name="Beta Buyer 0",
        org_id=org_beta,
        owner_user_id="user-beta",
    )

    path_alpha = card_file_path(agent_id, org_alpha)
    path_beta = card_file_path(agent_id, org_beta)

    # 1. Distinct filesystem paths
    assert path_alpha != path_beta
    assert path_alpha.exists()
    assert path_beta.exists()
    assert path_alpha.name == f"{org_alpha}__{agent_id}.json"
    assert path_beta.name == f"{org_beta}__{agent_id}.json"

    # 2. Both cards retain their respective contents (no last-writer-wins overwrite)
    assert card_alpha.display_name == "Alpha Buyer 0"
    assert card_beta.display_name == "Beta Buyer 0"
    assert card_alpha.org_id == org_alpha
    assert card_beta.org_id == org_beta

    # 3. Verification isolation: org_alpha card verifies only for org_alpha
    assert verify_agent_card(path_alpha, expected_org_id=org_alpha) is True
    assert verify_agent_card(path_alpha, expected_org_id=org_beta) is False

    # 4. Verification isolation: org_beta card verifies only for org_beta
    assert verify_agent_card(path_beta, expected_org_id=org_beta) is True
    assert verify_agent_card(path_beta, expected_org_id=org_alpha) is False


def test_get_or_create_agent_card_org_scoped(tmp_path, monkeypatch):
    """Assert get_or_create_agent_card retrieves correct org card without collisions."""
    monkeypatch.setenv("AGENT_CARD_DIR", str(tmp_path))

    agent_id = "buyer-0"
    org_1 = "org-1"
    org_2 = "org-2"

    card1, sig1 = get_or_create_agent_card(
        agent_id=agent_id,
        role="buyer",
        org_id=org_1,
        display_name="Org 1 Buyer",
    )

    card2, sig2 = get_or_create_agent_card(
        agent_id=agent_id,
        role="buyer",
        org_id=org_2,
        display_name="Org 2 Buyer",
    )

    path1 = card_file_path(agent_id, org_1)
    path2 = card_file_path(agent_id, org_2)

    assert path1.exists()
    assert path2.exists()

    # Re-fetch both and ensure idempotency
    refetched1, _ = get_or_create_agent_card(agent_id=agent_id, role="buyer", org_id=org_1)
    refetched2, _ = get_or_create_agent_card(agent_id=agent_id, role="buyer", org_id=org_2)

    assert refetched1.display_name == "Org 1 Buyer"
    assert refetched2.display_name == "Org 2 Buyer"
