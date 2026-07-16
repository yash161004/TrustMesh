"""
TrustMesh LLM Client — Phase 1: Agent Logic

Provides a unified interface for calling Gemini and Groq APIs.
Supports streaming responses for real-time negotiation.

Mock mode is automatically enabled when API keys are empty or
contain placeholder values (e.g., "your_gemini_api_key_here").

Phase 1 refactor: The mock generator uses scenario data from the
context dict so it produces realistic, scenario-appropriate offers
for ANY product/pricing scenario — not just the office-chairs default.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

import httpx

from .config import get_settings


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERNS = [
    "your_",
    "placeholder",
    "xxxxxxxxx",
    "sk-your",
    "enter_your",
]


def _is_placeholder(key: str) -> bool:
    """Return True if the key looks like a placeholder, not a real key."""
    lowered = key.lower().strip()
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern in lowered:
            return True
    return False


def _resolve_api_key(key: str) -> str:
    """Return empty string for placeholder keys, the key otherwise."""
    if not key:
        return ""
    if _is_placeholder(key):
        return ""
    return key


# ---------------------------------------------------------------------------
# Mock response helpers
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}


def _sym(currency: str) -> str:
    return _CURRENCY_SYMBOLS.get(currency, currency + " ")


def _extract_scenario(context_data: dict) -> dict:
    """Extract scenario fields from the context dict with sensible defaults."""
    scenario = context_data.get("scenario", {})
    if isinstance(scenario, dict) and scenario:
        return scenario
    # Fall back to flat scenario_xxx fields for backwards compatibility
    return {
        "product_name": context_data.get("scenario_product", "items"),
        "quantity": context_data.get("scenario_quantity", 100),
        "currency": context_data.get("scenario_currency", "INR"),
        "market_reference_price": context_data.get("scenario_market_ref", 480.0),
        "buyer_budget_cap": context_data.get("scenario_buyer_cap", 500.0),
        "buyer_target_price": context_data.get("scenario_buyer_target", 440.0),
        "seller_floor_price": context_data.get("scenario_seller_floor", 420.0),
        "seller_asking_price": context_data.get("scenario_seller_ask", 550.0),
        "delivery_preference_days": context_data.get("scenario_delivery_days", 14),
        "standard_delivery_days": context_data.get("scenario_standard_delivery", 21),
        "expedited_delivery_days": context_data.get("scenario_expedited_days"),
        "expedited_premium_per_unit": context_data.get("scenario_expedited_premium"),
    }


def _mock_response_generic(messages: list[dict]) -> str:
    """Return a scenario-aware mock response.

    Reads scenario fields from the context (which was placed there by
    the SessionManager) and generates realistic multi-turn negotiation
    that converges toward a deal for ANY product/pricing profile.
    """
    # --- Extract context (last message - the action prompt) ---
    context_msg = messages[-1]["content"] if len(messages) >= 1 else "{}"
    try:
        context_data = json.loads(context_msg).get("context", {})
    except (json.JSONDecodeError, TypeError):
        context_data = {}

    scenario = _extract_scenario(context_data)

    last_price = float(context_data.get("last_price", scenario["market_reference_price"]))
    turn_number = int(context_data.get("turn", 1))
    role = str(context_data.get("role", "buyer"))

    product = scenario["product_name"]
    qty = int(scenario["quantity"])
    currency = scenario["currency"]
    sym = _sym(currency)
    market_ref = float(scenario["market_reference_price"])
    buyer_cap = float(scenario["buyer_budget_cap"])
    buyer_target = float(scenario["buyer_target_price"])
    seller_floor = float(scenario["seller_floor_price"])
    seller_ask = float(scenario["seller_asking_price"])
    delivery_pref = int(scenario.get("delivery_preference_days", 14))
    standard_delivery = int(scenario.get("standard_delivery_days", 21))
    expedited_days = scenario.get("expedited_delivery_days")
    expedited_premium = scenario.get("expedited_premium_per_unit")

    # --- Determine the "sweet spot" zone — price range where both sides can deal ---
    # Buyer will accept at or below buyer_cap, but ideally at buyer_target
    # Seller will accept at or above seller_floor, but ideally at seller_ask
    # The deal zone is the overlap between [buyer_target, buyer_cap] and [seller_floor, seller_ask]
    deal_low = max(buyer_target, seller_floor)
    deal_high = min(buyer_cap, seller_ask)
    # Midpoint is the natural convergence point
    deal_mid = round((deal_low + deal_high) / 2, 2)
    # If no overlap, force an impasse
    no_deal_zone = deal_low > deal_high

    # --- Extract the actual last offer message for detecting delivery terms ---
    last_offer_msg = messages[-2]["content"] if len(messages) >= 2 else "{}"
    try:
        last_offer = json.loads(last_offer_msg)
        last_terms = str(last_offer.get("delivery_terms", ""))
    except (json.JSONDecodeError, TypeError):
        last_terms = ""

    # --- Accept / reject triggers ---
    if no_deal_zone:
        # Price ranges don't overlap — eventual rejection
        if turn_number >= 6:
            return json.dumps({
                "message_type": "REJECT",
                "price": 0,
                "quantity": 0,
                "delivery_terms": "",
                "notes": (
                    f"Unable to reach agreement after {turn_number} turns. "
                    f"Buyer's maximum ({sym}{buyer_cap:.2f}) is below seller's minimum ({sym}{seller_floor:.2f}). "
                    f"Negotiation impasse."
                ),
            })

    # Accept when price falls within the deal zone, later turns = more willing
    accept_turn_threshold = 5 if last_price >= deal_low and last_price <= deal_high else 10
    if turn_number >= accept_turn_threshold and deal_low <= last_price <= deal_high:
        return json.dumps({
            "message_type": "ACCEPT",
            "price": last_price,
            "quantity": qty,
            "delivery_terms": (
                f"Delivery within {delivery_pref} days, Net-30, "
                f"finalised at {sym}{last_price:.2f}/unit"
            ),
            "notes": (
                f"Agreed at {sym}{last_price:.2f}/unit for {qty} {product}. "
                f"Deal closed after {turn_number} turns."
            ),
        })

    if turn_number >= 9:
        # Forced acceptance at a compromise price
        compromise_price = round((last_price + deal_mid) / 2, 2) if not no_deal_zone else last_price
        return json.dumps({
            "message_type": "ACCEPT",
            "price": compromise_price,
            "quantity": qty,
            "delivery_terms": (
                f"Compromised delivery, final at {sym}{compromise_price:.2f}/unit"
            ),
            "notes": f"Accepting at {sym}{compromise_price:.2f}/unit after extended negotiation.",
        })

    if turn_number >= 12:
        return json.dumps({
            "message_type": "REJECT",
            "price": 0,
            "quantity": 0,
            "delivery_terms": "",
            "notes": f"Unable to reach agreement after maximum negotiation turns for {product}.",
        })

    # --- Seller: responding to buyer's offer ---
    if role == "seller":
        # Seller counters upward from last_price, approaching seller_ask
        increment = max(0.08 - (turn_number * 0.01), 0.02)  # 8% → 2%
        counter_price = round(last_price * (1 + increment), 2)
        counter_price = min(counter_price, seller_ask)

        if turn_number >= 3:
            delivery_text = (
                f"Delivery within {delivery_pref} days at {sym}{counter_price:.2f}/unit "
                f"(expedited, +{sym}{expedited_premium:.2f}/unit premium waived for {qty}-unit volume)"
                if expedited_days and expedited_premium
                else f"Delivery within {delivery_pref} days at {sym}{counter_price:.2f}/unit"
            )
        else:
            delivery_text = (
                f"Standard delivery within {standard_delivery} days, Net-15, "
                f"2-year warranty on manufacturing defects"
            )

        return json.dumps({
            "message_type": "COUNTER_OFFER",
            "price": counter_price,
            "quantity": qty,
            "delivery_terms": delivery_text,
            "notes": (
                f"Counter at {sym}{counter_price:.2f}/unit. "
                f"Standard {standard_delivery}-day delivery included."
                + (f" {expedited_days}-day expedite available." if expedited_days else "")
            ),
        })

    # --- Buyer: responding to seller's offer ---
    decrement = max(0.06 - (turn_number * 0.008), 0.015)  # 6% → 1.5%
    counter_price = round(last_price * (1 - decrement), 2)
    counter_price = max(counter_price, buyer_target)

    if turn_number >= 4:
        delivery_text = (
            f"Delivery within {delivery_pref} days required, Net-30, "
            f"at {sym}{counter_price:.2f}/unit — final delivery requirement"
        )
    else:
        delivery_text = (
            f"Delivery within {delivery_pref} days preferred, Net-30, "
            f"FOB destination, quality inspection on arrival"
        )

    return json.dumps({
        "message_type": "COUNTER_OFFER",
        "price": counter_price,
        "quantity": qty,
        "delivery_terms": delivery_text,
        "notes": f"Counter at {sym}{counter_price:.2f}/unit. Requiring {delivery_pref}-day delivery.",
    })


# ---------------------------------------------------------------------------
# Abstract client
# ---------------------------------------------------------------------------


class LLMClient(ABC):
    """Abstract base class for LLM API clients."""

    @abstractmethod
    async def generate(self, messages: list[dict], system: str = "") -> str:
        """Generate a response from the LLM."""
        ...

    @abstractmethod
    async def generate_stream(self, messages: list[dict], system: str = "") -> AsyncIterator[str]:
        """Generate a streaming response from the LLM."""
        ...


# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------


class GeminiClient(LLMClient):
    """Google Gemini API client."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        resolved_key = _resolve_api_key(api_key)
        self.api_key = resolved_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, messages: list[dict], system: str = "") -> str:
        """Generate a response from Gemini."""
        if not self.api_key:
            return _mock_response_generic(messages)

        contents = self._format_messages(messages, system)
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"contents": contents},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def generate_stream(self, messages: list[dict], system: str = "") -> AsyncIterator[str]:
        """Generate a streaming response from Gemini."""
        if not self.api_key:
            async for chunk in self._mock_stream(messages):
                yield chunk
            return

        contents = self._format_messages(messages, system)
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?key={self.api_key}"

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                url,
                json={
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": 1024},
                },
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "candidates" in data:
                            yield data["candidates"][0]["content"]["parts"][0]["text"]

    def _format_messages(self, messages: list[dict], system: str) -> list[dict]:
        """Format messages for Gemini API."""
        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        return contents

    async def _mock_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield mock streaming response."""
        response = _mock_response_generic(messages)
        words = response.split()
        for word in words:
            yield word + " "


# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------


class GroqClient(LLMClient):
    """Groq API client (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        resolved_key = _resolve_api_key(api_key)
        self.api_key = resolved_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"

    async def generate(self, messages: list[dict], system: str = "") -> str:
        """Generate a response from Groq."""
        if not self.api_key:
            return _mock_response_generic(messages)

        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "model": self.model,
                    "messages": formatted_messages,
                    "max_tokens": 1024,
                },
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def generate_stream(self, messages: list[dict], system: str = "") -> AsyncIterator[str]:
        """Generate a streaming response from Groq."""
        if not self.api_key:
            async for chunk in self._mock_stream(messages):
                yield chunk
            return

        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                url,
                json={
                    "model": self.model,
                    "messages": formatted_messages,
                    "max_tokens": 1024,
                    "stream": True,
                },
                headers=headers,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data = json.loads(line[6:])
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]

    async def _mock_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield mock streaming response."""
        response = _mock_response_generic(messages)
        words = response.split()
        for word in words:
            yield word + " "


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_llm_client(provider: str = "gemini") -> LLMClient:
    """Factory function to get the appropriate LLM client.

    Automatically falls back to mock mode if the API key for the
    requested provider is empty, missing, or a placeholder value.

    Special cases:
    - provider="mock" → always returns a client with empty API key (mock mode)
    - provider="gemini" with no valid key → falls through to mock
    - provider="groq" with no valid key → falls through to mock
    """
    settings = get_settings()

    if provider.lower() == "mock":
        return GeminiClient(api_key="")  # Force mock mode

    if provider.lower() == "groq":
        key = _resolve_api_key(settings.groq_api_key)
        if not key:
            return GeminiClient(api_key="")  # Falls through to mock
        return GroqClient(api_key=key)

    key = _resolve_api_key(settings.gemini_api_key)
    if not key:
        return GeminiClient(api_key="")  # Falls through to mock
    return GeminiClient(api_key=key)
