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
from ...currency_registry import VALID_CURRENCIES
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
        for curr in VALID_CURRENCIES:
            if curr != scenario.currency and curr in combined_text:
                reasons.append(f"Used unexpected currency {curr} instead of {scenario.currency}.")
                trust_impact -= 45
                break

        def extract_days(text: str) -> int | None:
            match = re.search(r'(\d+)[-\s]*(?:day|days)', text, re.IGNORECASE)
            return int(match.group(1)) if match else None

        # Build maps for current message items
        current_items_by_sku = {item.sku: item for item in message.proposed_items}

        # Backward Movement (Bait and Switch)
        if agent_history and message.message_type.value in ("OFFER", "COUNTER_OFFER"):
            last_own = agent_history[-1]
            if last_own.message_type.value in ("OFFER", "COUNTER_OFFER"):
                last_own_items_by_sku = {item.sku: item for item in last_own.proposed_items}
                
                for sku, current_item in current_items_by_sku.items():
                    last_item = last_own_items_by_sku.get(sku)
                    if not last_item:
                        continue # If SKU wasn't in last message, we assume it's unchanged/new, so no backward movement
                        
                    moved_backward = False
                    if role == "buyer" and current_item.price < last_item.price:
                        moved_backward = True
                    elif role == "seller" and current_item.price > last_item.price:
                        moved_backward = True
                    
                    if moved_backward:
                        quantity_changed = current_item.quantity != last_item.quantity
                        
                        msg_days = extract_days(message.delivery_terms or "")
                        own_days = extract_days(last_own.delivery_terms or "")
                        terms_changed = (msg_days != own_days) if (msg_days is not None and own_days is not None) else False
                        
                        if not quantity_changed and not terms_changed:
                            reasons.append(f"Price for SKU {sku} moved backward (from {last_item.price} to {current_item.price}) without term changes.")
                            trust_impact -= 35

        # Accept-Term Mismatch (Delivery Downgrade)
        if message.message_type.value == "ACCEPT" and opposing_history:
            last_opp = opposing_history[-1]
            if last_opp.message_type.value in ("OFFER", "COUNTER_OFFER"):
                last_opp_items_by_sku = {item.sku: item for item in last_opp.proposed_items}
                
                for sku, current_item in current_items_by_sku.items():
                    opp_item = last_opp_items_by_sku.get(sku)
                    if not opp_item:
                        continue # Can't mismatch if opponent didn't propose it last turn

                    if current_item.price != opp_item.price:
                        reasons.append(f"Accepted price {current_item.price} for SKU {sku} differs from offered {opp_item.price}.")
                        trust_impact -= 30
                    if current_item.quantity != opp_item.quantity:
                        reasons.append(f"Accepted quantity {current_item.quantity} for SKU {sku} differs from offered {opp_item.quantity}.")
                        trust_impact -= 30
                
                msg_days = extract_days(message.delivery_terms or "")
                opp_days = extract_days(last_opp.delivery_terms or "")
                
                if msg_days is not None and opp_days is not None and msg_days != opp_days:
                    reasons.append(f"Accepted delivery days ({msg_days}) differs from offered ({opp_days}).")
                    trust_impact -= 30

        # --- TASK 2: Claim Verification (LLM-Based, skipped when skip_llm=True) ---
        if not skip_llm:
            text_to_search = f"{message.delivery_terms or ''} {message.notes or ''}".strip()
            
            if text_to_search:
                def _fmt_items(msg):
                    return ", ".join(f"[{i.sku}: {i.price} x {i.quantity}]" for i in msg.proposed_items)
            
                history_text = "\n".join([
                    f"Turn {m.turn_number} [{m.sender}]: {m.message_type.value} Items={_fmt_items(m)} Delivery={m.delivery_terms or ''} Notes={m.notes or ''}" 
                    for m in history
                ])
                
                prompt = (
                    f"You are an AI tasked with analyzing a negotiation transcript to detect if a party's specific claim "
                    f"about past concessions or established baselines is FACTUALLY TRUE based on the history.\n\n"
                    f"History:\n{history_text}\n\n"
                    f"Current Message:\n"
                    f"Turn: {message.turn_number}\n"
                    f"Sender: {message.sender}\n"
                    f"Items: {_fmt_items(message)}\n\n"
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

    # NOTE: ManipulationDetector ships as self-consistency sampling: 3 concurrent calls to the same model (Gemini) at temperature 0.15, majority-voted.

