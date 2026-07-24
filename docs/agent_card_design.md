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

1. Generate a signed AgentCard JSON per agent, bound to its `org_id` and `owner_user_id` from the authenticated request context.
2. Sign the card's contents with a **per-agent** Ed25519 keypair (`load_or_generate_keypair_for_agent(agent_id)`) — the same primitive family used for ledger signing, but keyed to the individual agent rather than a shared role key.
3. Write the signed card to an **org-scoped** path: `backend/data/agent_cards/{org_id}__{agent_id}.json` (or `{agent_id}.json` for a legacy, un-scoped card). The `{org_id}__` prefix is what keeps two organizations that default to the same agent id (e.g. `buyer-agent-001`) from colliding on one key file.
4. Provide `verify_agent_card(path, expected_org_id=...)` that recomputes the canonical-JSON payload, confirms the Ed25519 signature matches, **and** rejects the card if the `org_id` inside its content does not match the expected org — the same tamper-evidence pattern used throughout TrustMesh, now extended to tenancy. The org check reads the card's *content*, not the resolved filename, so a stale un-scoped file cannot be used to bypass isolation.

### Key design decisions

| Decision | Rationale |
|---|---|
| Ed25519 only (no new crypto) | Reuses the existing keypair from `app.crypto.signing` — the same keys already signing ledger entries. No new key management surface. |
| Canonical JSON signing | Uses the same `canonical_json()` deterministic serializer as the ledger, ensuring signature portability across environments. |
| Detached signature | The AgentCard payload and its signature are stored side-by-side in the same JSON file (under `card` and `signature` keys), mirroring the ERC-8004 convention of a resolvable document that can be verified independently. |
| Local filesystem | Since TrustMesh has no on-chain integration, `data/agent_cards/` serves as the local equivalent of the `tokenURI` endpoint. In production this would be served from IPFS or an HTTPS endpoint registered on-chain. |
| Per-agent, org-scoped keys | Cards are generated per agent via `load_or_generate_keypair_for_agent(agent_id)` and persisted under an `{org_id}__{agent_id}.json` path. This replaced the earlier shared per-role key, which let agents in different orgs collide on one key file (whichever org signed first owned it; every other org's messages then failed the tenancy check and silently did not sign). |
| Content-based tenancy check | `verify_agent_card` compares the `org_id` stored *inside* the card payload against the caller's expected org, not the filename it was loaded from. The filename prefix is only a lookup convenience; the authorization decision is always made against signed content. |

## Limitations (explicitly stated)

- **Not on-chain.** These cards live on the local filesystem, not in an ERC-8004 Identity Registry or any smart contract. There is no NFT mint, no on-chain resolution, and no cross-agent discoverability.
- **No reputation registry.** ERC-8004's Reputation and Validation registries are not implemented. The trust scores produced by TrustMesh's Trust Engine are not written to any on-chain reputation oracle.
- **No expiry/rotation.** Cards have a `created_at` timestamp and version field but no built-in expiry mechanism or key rotation workflow.
- **File-path tenancy, not a DB authority.** Isolation rests on the `{org_id}__{agent_id}.json` path plus the content-based org check in `verify_agent_card`. An alternative design — a DB-backed `AgentIdentityRecord` per `(org, role)` as the single verification authority — was prototyped on `chore/phase-0-credibility-pass` (commit `9fd53cd`) but deliberately **not merged**; the file-path approach is the shipped one. See the roadmap's Phase 1 entry for the rationale behind that choice.

This is a locally-verifiable proof-of-concept demonstrating that the same cryptographic primitives used for ledger tamper-evidence can produce machine-readable identity descriptors in the ERC-8004 style. Wiring the cards to an on-chain registry or serving them via HTTPS would be follow-on work.

## Current state & identity hardening

As of the multi-tenant hardening pass, AgentCard identity is wired into the live request path rather than being a standalone artifact:

- **Signing at message creation.** `SessionManager._persist_message` resolves the signer's card via `card_file_path(msg.sender, org_id)`, lazily provisioning an org-bound card if none exists, and signs every `NegotiationMessage` before it is appended to the ledger. A card that resolves to a different org fails `verify_agent_card` and the message is not signed under the wrong tenant's key.
- **Org-filtered inspection.** `routes/agent_cards.py` scopes lookups to `current_user.org_id` and returns `403` on a cross-org card request, with an explicit role-gated admin bypass (`role in ("admin", "system")`) — the bypass is role-gated, never path-gated.
- **Legacy fallback.** When no org-scoped card exists yet, resolution falls back to a legacy un-scoped `{agent_id}.json` file. This is a migration convenience only; because the org check is content-based, a legacy file belonging to another org still fails verification and cannot reopen the cross-tenant gap.

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
