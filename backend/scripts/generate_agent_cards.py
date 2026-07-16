"""
TrustMesh AgentCard Generator

Generates and cryptographically signs an ERC-8004-style AgentCard for
each of the defined agent roles (buyer, seller), then self-verifies every
card to confirm tamper-evidence works end-to-end.

Usage:
    python scripts/generate_agent_cards.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.identity.agent_card import (
    generate_agent_card,
    verify_agent_card,
    card_file_path,
    CARDS_DIR,
)
from app.db import AgentIdentityRecord
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session


def main():
    roles = ["buyer", "seller"]
    generated = []

    print("=" * 52)
    print("  TrustMesh AgentCard Generator")
    print("=" * 52)

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_path = os.path.join(os.path.dirname(__file__), "..", "trustmesh.db")
        db_url = f"sqlite:///{os.path.abspath(db_path)}"
    else:
        db_url = db_url.replace("+aiosqlite", "")
    engine = create_engine(db_url)
    
    agent_id_map = {}
    with Session(engine) as db:
        for rec in db.execute(select(AgentIdentityRecord)).scalars().all():
            agent_id_map[rec.role.lower()] = rec.id

    for role in roles:
        print(f"\n  Generating AgentCard for role: {role}")
        db_id = agent_id_map.get(role)
        card, sig = generate_agent_card(role, agent_id=db_id)
        path = card_file_path(card.agent_id)
        generated.append((role, card, path))
        print(f"    agent_id   : {card.agent_id}")
        print(f"    display    : {card.display_name}")
        print(f"    capabilities: {len(card.capabilities)} entries")
        print(f"    version    : {card.version}")
        print(f"    path       : {path}")
        print(f"    signature  : {sig[:32]}...")

    print("\n" + "=" * 52)
    print("  Self-verification")
    print("=" * 52)

    all_ok = True
    for role, card, path in generated:
        result = verify_agent_card(path)
        status = "PASS" if result else "FAIL"
        if not result:
            all_ok = False
        print(f"  {role:>8s} ({card.agent_id[:8]}...) -> {status}")

    # Also verify that tampering with a card file causes verification failure
    print("\n  Tamper test: modifying a card file on disk...")
    import json

    first_path = card_file_path(generated[0][1].agent_id)
    data = json.loads(first_path.read_text())
    data["card"]["display_name"] = "Tampered Agent"
    first_path.write_text(json.dumps(data, indent=2, default=str))
    tamper_result = verify_agent_card(first_path)
    if not tamper_result:
        print("  -> PASS (tampered card correctly rejected)")
    else:
        print("  -> FAIL (tampered card was NOT rejected)")
        all_ok = False

    # Clean up the tampered file so regenerate creates a fresh one
    if first_path.exists():
        first_path.unlink()

    # Regenerate to restore the tampered card
    print("  Restoring tampered card...")
    restored_card, restored_sig = generate_agent_card(generated[0][0], agent_id=generated[0][1].agent_id)
    restore_result = verify_agent_card(card_file_path(restored_card.agent_id))
    restore_label = "PASS" if restore_result else "FAIL"
    print(f"  -> {restore_label} (restored card verified)")
    print("\n" + "=" * 52)
    if all_ok:
        print("  All AgentCards generated and verified successfully.")
        print(f"  Cards stored in: {CARDS_DIR}")
    else:
        print("  Some verifications FAILED.")
        sys.exit(1)
    print("=" * 52)


if __name__ == "__main__":
    main()
