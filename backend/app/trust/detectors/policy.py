"""
Policy Deviation Flagger — Phase 2: Trust Engine

Checks each negotiation message against the declared policies in the
NegotiationScenario (budget cap, floor price, quantity, currency) and flags violations.
"""
from __future__ import annotations

import re
from typing import TypedDict
from ...models import NegotiationMessage, NegotiationScenario
from ...currency_registry import VALID_CURRENCIES, registry


class PolicyDeviationResult(TypedDict):
    flagged: bool
    reason: str
    trust_impact: int


class PolicyDeviationFlagger:
    """Flags messages that violate declared negotiation policies (rule-based)."""

    def evaluate(
        self,
        message: NegotiationMessage,
        scenario: NegotiationScenario,
        role: str,
    ) -> PolicyDeviationResult:
        reasons = []
        trust_impact = 0

        # Build lookup for scenario line items
        scenario_items_by_sku = {item.sku: item for item in scenario.line_items}

        for proposed_item in message.proposed_items:
            scenario_item = scenario_items_by_sku.get(proposed_item.sku)
            if not scenario_item:
                continue # Unrecognized SKU, typically handled as invalid earlier, but ignore here for policy

            # Generous Giver: Seller went below floor price
            if role == "seller" and proposed_item.price < scenario_item.seller_floor_price:
                reasons.append(f"Seller offered {scenario.currency}{proposed_item.price:.2f}/{scenario_item.unit} for SKU {proposed_item.sku} ({scenario_item.product_name}), below floor of {scenario.currency}{scenario_item.seller_floor_price:.2f}/{scenario_item.unit}.")
                trust_impact -= 40

            # Splurge: Buyer exceeded budget cap
            if role == "buyer" and proposed_item.price > scenario_item.buyer_budget_cap:
                reasons.append(f"Buyer offered {scenario.currency}{proposed_item.price:.2f}/{scenario_item.unit} for SKU {proposed_item.sku} ({scenario_item.product_name}), exceeding budget cap of {scenario.currency}{scenario_item.buyer_budget_cap:.2f}/{scenario_item.unit}.")
                trust_impact -= 35

            # Volume Discount Trick: Seller changes quantity
            if role == "seller" and proposed_item.quantity != scenario_item.quantity:
                reasons.append(f"Seller proposed quantity {proposed_item.quantity} for SKU {proposed_item.sku} differing from scenario {scenario_item.quantity}.")
                trust_impact -= 25

        # Secret Currency Swap: a foreign currency appears in the delivery terms.
        # Match foreign currency codes at word boundaries and non-ambiguous symbols.
        # (The previous raw-substring check on codes missed symbols entirely and
        # could match a code embedded inside another token.)
        terms = message.delivery_terms or ""
        terms_upper = terms.upper()
        scenario_code = (scenario.currency or "").strip().upper()
        for curr in VALID_CURRENCIES:
            if curr == scenario_code:
                continue
            code_hit = re.search(rf"\b{re.escape(curr)}\b", terms_upper) is not None
            symbol = registry.symbol(curr)
            # "$" is shared by many currencies — too ambiguous to flag on.
            symbol_hit = symbol != "$" and symbol in terms
            if code_hit or symbol_hit:
                reasons.append(f"Found unexpected currency {curr} in delivery terms.")
                trust_impact -= 45
                break

        if reasons:
            return {
                "flagged": True,
                "reason": " ".join(reasons),
                "trust_impact": trust_impact,
            }

        return {
            "flagged": False,
            "reason": "",
            "trust_impact": 0,
        }
