"""
Commitment Consistency Checker — Phase 2: Trust Engine

Flags contradictions, broken commitments, and false claims.
KNOWN LIMITATION: Claim extraction relies on deterministic regex/heuristics 
which are fragile to phrasing variations. Future upgrades should use semantic 
LLM extraction.
"""
from __future__ import annotations

import re
import json
from typing import TypedDict
from ...models import NegotiationMessage, NegotiationScenario
from ...llm_client import get_llm_client

class ConsistencyResult(TypedDict):
    flagged: bool
    reason: str
    trust_impact: int

class CommitmentConsistencyChecker:
    """Tracks promises in negotiation and flags broken commitments and false claims."""
    
    def __init__(self, max_retries: int = 3):
        self.llm = get_llm_client()
        self.max_retries = max_retries

    async def evaluate(
        self,
        message: NegotiationMessage,
        history: list[NegotiationMessage],
        scenario: NegotiationScenario,
        skip_llm: bool = False,
    ) -> ConsistencyResult:
        reasons = []
        trust_impact = 0

        agent_history = [m for m in history if m.sender == message.sender]
        opposing_history = [m for m in history if m.sender != message.sender]
        role = "buyer" if "buyer" in message.sender else "seller"

        # --- TASK 1: Structural Checks ---
        
        # Secret Currency Swap
        combined_text = f"{message.delivery_terms or ''} {message.notes or ''}".upper()
        currencies = ["USD", "EUR", "GBP", "INR", "JPY"]
        for curr in currencies:
            if curr != scenario.currency and curr in combined_text:
                reasons.append(f"Used unexpected currency {curr} instead of {scenario.currency}.")
                trust_impact -= 45
                break

        # Backward Movement (Bait and Switch)
        if agent_history and message.message_type.value in ("OFFER", "COUNTER_OFFER"):
            last_own = agent_history[-1]
            if last_own.message_type.value in ("OFFER", "COUNTER_OFFER"):
                moved_backward = False
                if role == "buyer" and message.price < last_own.price:
                    moved_backward = True
                elif role == "seller" and message.price > last_own.price:
                    moved_backward = True
                
                if moved_backward:
                    quantity_changed = message.quantity != last_own.quantity
                    
                    def extract_days(text: str) -> int | None:
                        match = re.search(r'(\d+)[-\s]*(?:day|days)', text, re.IGNORECASE)
                        return int(match.group(1)) if match else None

                    msg_days = extract_days(message.delivery_terms or "")
                    own_days = extract_days(last_own.delivery_terms or "")
                    terms_changed = (msg_days != own_days) if (msg_days is not None and own_days is not None) else False
                    
                    if not quantity_changed and not terms_changed:
                        reasons.append(f"Price moved backward (from {last_own.price} to {message.price}) without term changes.")
                        trust_impact -= 35

        # Accept-Term Mismatch (Delivery Downgrade)
        if message.message_type.value == "ACCEPT" and opposing_history:
            last_opp = opposing_history[-1]
            if last_opp.message_type.value in ("OFFER", "COUNTER_OFFER"):
                if message.price != last_opp.price:
                    reasons.append(f"Accepted price {message.price} differs from offered {last_opp.price}.")
                    trust_impact -= 30
                if message.quantity != last_opp.quantity:
                    reasons.append(f"Accepted quantity {message.quantity} differs from offered {last_opp.quantity}.")
                    trust_impact -= 30
                
                def extract_days(text: str) -> int | None:
                    match = re.search(r'(\d+)[-\s]*(?:day|days)', text, re.IGNORECASE)
                    return int(match.group(1)) if match else None
                
                msg_days = extract_days(message.delivery_terms or "")
                opp_days = extract_days(last_opp.delivery_terms or "")
                
                if msg_days is not None and opp_days is not None and msg_days != opp_days:
                    reasons.append(f"Accepted delivery days ({msg_days}) differs from offered ({opp_days}).")
                    trust_impact -= 30

        # --- TASK 2: Claim Verification (LLM-Based, skipped when skip_llm=True) ---
        if not skip_llm:
            text_to_search = f"{message.delivery_terms or ''} {message.notes or ''}".strip()
            
            if text_to_search:
                history_text = "\n".join([f"Turn {m.turn_number} [{m.sender}]: {m.message_type.value} Price={m.price} Qty={m.quantity} Delivery={m.delivery_terms or ''} Notes={m.notes or ''}" for m in history])
                
                prompt = (
                    f"You are a negotiation consistency checker.\n"
                    f"History:\n{history_text}\n\n"
                    f"Current message from {message.sender}:\n"
                    f"Text: '{text_to_search}'\n"
                    f"Price: {message.price}\n\n"
                    f"Does the current message make a factual claim about a prior offer, agreement, or concession? "
                    f"If so, is that claim true against the actual history provided?\n"
                    f"CRITICAL: Before flagging a concession or price-movement claim as false, you MUST explicitly "
                    f"show your work in the 'reasoning' field. Identify the claimed number, identify the actual "
                    f"numbers from history, compute the actual delta, and then state whether they match.\n"
                    f"Output strictly a JSON object exactly matching this format: "
                    f'{{"reasoning": "str", "makes_claim": bool, "claim_description": "str", "claim_supported_by_history": bool}}'
                )
                
                try:
                    response = await self.llm.generate([{"role": "user", "content": prompt}])
                    
                    # Strip markdown code blocks if present
                    clean_response = response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:-3]
                    elif clean_response.startswith("```"):
                        clean_response = clean_response[3:-3]
                    clean_response = clean_response.strip()
                    
                    llm_result = json.loads(clean_response)
                    
                    if llm_result.get("makes_claim") and not llm_result.get("claim_supported_by_history"):
                        desc = llm_result.get("claim_description", "Falsely claimed a prior agreement or concession.")
                        reasons.append(f"LLM flagged false claim: {desc}")
                        trust_impact -= 40
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"LLM claim verification failed: {e}")

        if reasons:
            return {
                "flagged": True,
                "reason": " ".join(reasons),
                "trust_impact": trust_impact
            }
            
        return {
            "flagged": False,
            "reason": "",
            "trust_impact": 0
        }

    # NOTE: ManipulationDetector ships as documented single-model classification.
    # Multi-provider majority-vote was attempted, invalidated by the cache-key
    # bug (fixed), and true parallel voting is infeasible on free-tier rate limits
    # — so it's a documented future direction, not a shipped feature.

