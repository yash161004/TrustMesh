"""
TrustMesh AgentCard Consistency Checker

Confirms that every AgentIdentity in the database has a valid signed
AgentCard on disk, and that every AgentCard file references an identity
that still exists (no orphaned/stale cards).

Usage:
    cd backend
    python scripts/check_agent_card_consistency.py
"""
from __future__ import annotations

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import init_db, close_db, get_all_agent_identities
from app.identity.agent_card import verify_agent_card, card_file_path, CARDS_DIR


async def main() -> int:
    await init_db()

    # ── Phase 1: Check every identity has a valid card ────────────────
    identities = await get_all_agent_identities()
    identity_ids = {i["id"] for i in identities}

    missing = []
    card_ok = []
    card_fail = []

    for ident in identities:
        cpath = card_file_path(ident["id"])
        if not cpath.exists():
            missing.append(ident["id"])
        elif verify_agent_card(cpath):
            card_ok.append(ident["id"])
        else:
            card_fail.append(ident["id"])

    # ── Phase 2: Scan for orphaned cards ──────────────────────────────
    orphaned_files = []
    if CARDS_DIR.exists():
        for fpath in sorted(CARDS_DIR.iterdir()):
            if fpath.suffix != ".json":
                continue
            import json
            try:
                data = json.loads(fpath.read_text())
                card_id = data.get("card", {}).get("agent_id", "")
                if card_id not in identity_ids:
                    orphaned_files.append((fpath.name, card_id))
            except Exception:
                orphaned_files.append((fpath.name, "<unparseable>"))

    # ── Summary ───────────────────────────────────────────────────────
    n_identities = len(identities)
    n_verified = len(card_ok)
    n_missing = len(missing)
    n_failed_verify = len(card_fail)
    n_orphaned = len(orphaned_files)

    print("=" * 56)
    print("  AgentCard Consistency Report")
    print("=" * 56)
    print(f"  Identities in DB        : {n_identities}")
    print(f"  Cards verified (PASS)   : {n_verified}")
    print(f"  Cards failed verify     : {n_failed_verify}")
    print(f"  Missing cards           : {n_missing}")
    print(f"  Orphaned card files     : {n_orphaned}")
    print()

    if n_missing:
        print("  Missing cards:")
        for iid in missing:
            print(f"    - {iid}")

    if n_failed_verify:
        print("  Cards that failed verification:")
        for iid in card_fail:
            print(f"    - {iid}")

    if orphaned_files:
        print("  Orphaned card files (no matching identity):")
        for fname, cid in orphaned_files:
            print(f"    - {fname}  (agent_id={cid})")

    any_issues = n_missing > 0 or n_failed_verify > 0 or n_orphaned > 0
    print()
    if any_issues:
        print("  Result: MISMATCH — see details above.")
    else:
        print("  Result: ALL CLEAN — every identity has a valid card,")
        print("          no orphaned files found.")
    print("=" * 56)

    await close_db()
    return 1 if any_issues else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
