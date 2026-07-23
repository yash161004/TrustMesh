# TrustMesh AgentCard: Local Identity Descriptor

## What is an ERC-8004 AgentCard?

ERC-8004 (Trustless Agents) is an Ethereum standard, deployed on mainnet in January 2026, that gives AI agents a **verifiable on-chain identity**. Co-authored by teams from MetaMask, Google, and Coinbase, it defines three core registries:

- **Identity Registry** — an ERC-721 NFT per agent whose `tokenURI` resolves to a JSON file (the "AgentCard") describing the agent's name, owner, and capabilities.
- **Reputation Registry** — a standard interface for posting and fetching feedback signals so agents build verifiable track records.
- **Validation Registry** — hooks for requesting independent verification of an agent's work (stake-secured re-execution, zkML, TEE attestations).

The AgentCard JSON at the `tokenURI` is the human-and-machine-facing identity document. It typically contains the agent's name, description, avatar image, and a list of services/skills/capabilities. Counterparties fetch this card before transacting to verify who they are dealing with.

See: [ERC-8004 specification](https://eips.ethereum.org/EIPS/eip-8004), [ERC-8004 Explorer](https://erc-8004.quicknode.com/learn/registries/identity)

## What We Implemented

TrustMesh implements a **local, file-system-based analog** of the ERC-8004 AgentCard pattern. Instead of minting an on-chain NFT, we:

1. Generate a signed AgentCard JSON for each agent role (buyer, seller).
2. Sign the card's contents with the agent's existing Ed25519 keypair (the same keys used for ledger signing).
3. Write the signed card to `backend/data/agent_cards/{agent_id}.json`.
4. Provide `verify_agent_card()` that recomputes the canonical-JSON payload and confirms the Ed25519 signature matches — the same tamper-evidence pattern used throughout TrustMesh.

### Key design decisions

| Decision | Rationale |
|---|---|
| Ed25519 only (no new crypto) | Reuses the existing keypair from `app.crypto.signing` — the same keys already signing ledger entries. No new key management surface. |
| Canonical JSON signing | Uses the same `canonical_json()` deterministic serializer as the ledger, ensuring signature portability across environments. |
| Detached signature | The AgentCard payload and its signature are stored side-by-side in the same JSON file (under `card` and `signature` keys), mirroring the ERC-8004 convention of a resolvable document that can be verified independently. |
| Local filesystem | Since TrustMesh has no on-chain integration, `data/agent_cards/` serves as the local equivalent of the `tokenURI` endpoint. In production this would be served from IPFS or an HTTPS endpoint registered on-chain. |
| Per-agent key generation | Cards are generated per agent using `load_or_generate_keypair_for_agent(agent_id)` and signing at message time uses the per-agent key (`sign_message_for_agent`). Keys are reused if they already exist for that `agent_id`. (See §"Current State & Identity Hardening" for the important caveat that default `agent_id`s are shared constants.) |

## Limitations (explicitly stated)

- **Not on-chain.** These cards live on the local filesystem, not in an ERC-8004 Identity Registry or any smart contract. There is no NFT mint, no on-chain resolution, and no cross-agent discoverability.
- **No reputation registry.** ERC-8004's Reputation and Validation registries are not implemented. The trust scores produced by TrustMesh's Trust Engine are not written to any on-chain reputation oracle.
- **Per-agent keys, but shared-constant default IDs.** Signing uses a per-agent keypair keyed on `agent_id`, not a single per-role key — but the API defaults `agent_id` to shared constants (`buyer-agent-001`/`seller-agent-001`), so distinct tenants collide on one key file unless they pass unique IDs. See §"Current State & Identity Hardening" for the full consequence. ERC-8004 envisions per-agent keys with dynamic wallet binding.
- **No expiry/rotation.** Cards have a `created_at` timestamp and version field but no built-in expiry mechanism or key rotation workflow.

This is a locally-verifiable proof-of-concept demonstrating that the same cryptographic primitives used for ledger tamper-evidence can produce machine-readable identity descriptors in the ERC-8004 style. The cards are already integrated with the session manager's signing path (see below); wiring them to an on-chain registry or serving them via HTTPS would be follow-on work.

## Current State & Identity Hardening (audited 2026-07-23)

**What is actually wired (since 2026-07-22, commit `6828ca7`).** The AgentCard is not a parked offline utility — it is in the live request path. On every message, `session_manager._persist_message`:

1. Derives the agent role from the sender vs. the session's `buyer_agent_id`/`seller_agent_id`.
2. Calls `get_or_create_agent_card(agent_id=msg.sender, role=role, org_id=..., owner_user_id=...)`, binding the card to the authenticated org and user.
3. Enforces `verify_agent_card(card_path, expected_org_id=org_id)` — refusing to sign on an org mismatch.
4. Signs the message with the **per-agent** key (`sign_message_for_agent(msg_dict, msg.sender)`) and writes the signature + public key into the hash-chained ledger.

The older shared-per-role signing helpers (`sign_message(msg, role)`, `get_public_key_b64`, `generate_keypair(role)`) still exist but are **not used** in the request path.

**The real remaining weakness — multi-tenant identity collision.** The API defaults `buyer_agent_id`/`seller_agent_id` to the shared constants `buyer-agent-001` / `seller-agent-001` (`routes/sessions.py`). Because `get_or_create_agent_card` is idempotent on `agent_id`, the first org to use `buyer-agent-001` creates the card bound to *its* org; when a second org's session uses the same constant, `verify_agent_card(expected_org_id=org_B)` fails against the org_A-bound card, the sign step raises, and the message is persisted **without a signature or ledger entry** (the failure is caught and logged, not surfaced). Net effect: with default IDs, only one org per constant ever produces a valid ledger, and every other tenant silently loses tamper-evidence. This — not "unwired signing" — is the actual identity gap.

**Design for the fix (per-`(org, role)` identity, DB-backed).**

- Provision one `AgentIdentityRecord` per `(org_id, role)`; extend that table (currently `id/role/name/reputation` only) with `org_id`, `owner_user_id`, and `public_key` columns via an Alembic migration.
- Use the identity's UUID (not a shared constant) as the signing key identifier, so keys are unique per tenant and never collide.
- Make the DB `AgentIdentityRecord` the authority `verify_agent_card` checks against, instead of trusting the `org_id` field inside the card file it is verifying.
- Close the cross-org listing in `routes/agent_cards.py` (globs *all* cards on disk) and `routes/identities.py` (returns *all* identities) — both currently ignore the caller's org.
- Update `test_agent_card_cross_org_message_signing_blocked`: with org-scoped identities the property shifts from "cross-org signing is blocked at runtime" to "cross-org signing is structurally impossible (separate key namespaces)" — a stronger guarantee, but the test's assertion must change to match.

This is scoped as the corrected Phase 1 item #1 in `docs/TrustMesh_Master_Roadmap.md`. It carries an Alembic migration against staging Postgres and changes a security-relevant test, so it is intended to run as its own reviewed session rather than an incidental edit.

## Usage

```bash
# Generate AgentCards for all roles
python scripts/generate_agent_cards.py

# Verify a specific card
python -c "
from app.identity.agent_card import verify_agent_card
print(verify_agent_card('backend/data/agent_cards/<agent_id>.json'))
"
```

The script self-verifies all generated cards and prints a tamper test (modifies a card, confirms verification fails, then regenerates to restore).
