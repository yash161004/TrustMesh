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
| Role-based key generation | Cards are generated per role (buyer, seller) using `load_or_generate_keypair(role)`. If keys already exist from previous ledger operations, they are reused — the card is bound to the same identity the ledger already tracks. |

## Limitations (explicitly stated)

- **Not on-chain.** These cards live on the local filesystem, not in an ERC-8004 Identity Registry or any smart contract. There is no NFT mint, no on-chain resolution, and no cross-agent discoverability.
- **No reputation registry.** ERC-8004's Reputation and Validation registries are not implemented. The trust scores produced by TrustMesh's Trust Engine are not written to any on-chain reputation oracle.
- **Static role keys.** The current implementation uses one keypair per role shared across all sessions. ERC-8004 envisions per-agent keys with dynamic wallet binding.
- **No expiry/rotation.** Cards have a `created_at` timestamp and version field but no built-in expiry mechanism or key rotation workflow.

This is a locally-verifiable proof-of-concept demonstrating that the same cryptographic primitives used for ledger tamper-evidence can produce machine-readable identity descriptors in the ERC-8004 style. Wiring the cards to an on-chain registry, serving them via HTTPS, or integrating them with the session manager's identity model would be follow-on work.

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
