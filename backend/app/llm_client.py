"""
TrustMesh LLM Client — Phase 1: Agent Logic

Provides a unified interface for calling Gemini and Groq APIs.
Supports streaming responses for real-time negotiation.

Mock mode is automatically enabled when API keys are empty or
contain placeholder values (e.g., "your_gemini_api_key_here").
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

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
            return self._mock_response(messages)

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

    def _mock_response(self, messages: list[dict]) -> str:
        """Return a mock response when no API key is configured.

        Produces realistic multi-turn negotiation with prices that converge
        toward a deal over several rounds.

        The last message in `messages` is always the **context prompt**
        (``{"action": "respond_to_negotiation", ...}``), so we extract
        ``last_price`` from ``context.last_price`` and determine the sender
        role from the actual offer message at ``messages[-2]``.
        """
        # --- Extract context (last message - the action prompt) ---
        context_msg = messages[-1]["content"] if len(messages) >= 1 else "{}"
        try:
            context_data = json.loads(context_msg).get("context", {})
        except (json.JSONDecodeError, TypeError):
            context_data = {}

        last_price = float(context_data.get("last_price", 460.0))
        turn_number = int(context_data.get("turn", 1))
        role = str(context_data.get("role", "buyer"))

        # --- Extract the actual last offer message for detecting delivery terms ---
        # The second-to-last message (if any) is the previous agent's offer
        last_offer_msg = messages[-2]["content"] if len(messages) >= 2 else "{}"
        try:
            last_offer = json.loads(last_offer_msg)
            last_terms = str(last_offer.get("delivery_terms", ""))
        except (json.JSONDecodeError, TypeError):
            last_terms = ""

        lower_terms = last_terms.lower()

        # --- Accept / reject triggers ---
        if turn_number >= 6 and 440 <= last_price <= 480:
            return json.dumps({
                "message_type": "ACCEPT",
                "price": last_price,
                "quantity": 100,
                "delivery_terms": (
                    f"Delivery within 14 days, Net-30, finalised at ₹{last_price}/unit"
                ),
                "notes": f"Agreed at ₹{last_price}/unit for 100 chairs. Deal closed.",
            })

        if turn_number >= 8:
            return json.dumps({
                "message_type": "ACCEPT",
                "price": last_price,
                "quantity": 100,
                "delivery_terms": f"Compromised delivery, final at ₹{last_price}/unit",
                "notes": f"Accepting at ₹{last_price}/unit after extended negotiation.",
            })

        if turn_number >= 10:
            return json.dumps({
                "message_type": "REJECT",
                "price": 0,
                "quantity": 0,
                "delivery_terms": "",
                "notes": "Unable to reach agreement after maximum negotiation turns.",
            })

        # --- Seller: responding to buyer's offer ---
        if role == "seller":
            increment = max(0.08 - (turn_number * 0.01), 0.02)  # 8% → 2%
            counter_price = round(last_price * (1 + increment), 2)
            counter_price = min(counter_price, 520.0)

            if turn_number >= 3:
                delivery_text = (
                    f"Delivery within 14 days at ₹{counter_price}/unit "
                    f"(expedited, +₹25/unit premium waived for 100-unit volume)"
                )
            else:
                delivery_text = (
                    f"Standard delivery within 21 days, Net-15, "
                    f"2-year warranty on manufacturing defects"
                )

            return json.dumps({
                "message_type": "COUNTER_OFFER",
                "price": counter_price,
                "quantity": 100,
                "delivery_terms": delivery_text,
                "notes": (
                    f"Counter at ₹{counter_price}/unit. "
                    f"Standard 21-day delivery included. 10-day expedite available."
                ),
            })

        # --- Buyer: responding to seller's offer ---
        decrement = max(0.06 - (turn_number * 0.008), 0.015)  # 6% → 1.5%
        counter_price = round(last_price * (1 - decrement), 2)
        counter_price = max(counter_price, 440.0)

        if turn_number >= 4:
            delivery_text = (
                f"Delivery within 14 days required, Net-30, "
                f"at ₹{counter_price}/unit — final delivery requirement"
            )
        else:
            delivery_text = (
                f"Delivery within 14 days preferred, Net-30, "
                f"FOB destination, quality inspection on arrival"
            )

        return json.dumps({
            "message_type": "COUNTER_OFFER",
            "price": counter_price,
            "quantity": 100,
            "delivery_terms": delivery_text,
            "notes": f"Counter at ₹{counter_price}/unit. Requiring 14-day delivery.",
        })

    async def _mock_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield mock streaming response."""
        response = self._mock_response(messages)
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
            return self._mock_response(messages)

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

    def _mock_response(self, messages: list[dict]) -> str:
        """Return a mock response when no API key is configured."""
        last_msg = messages[-1]["content"] if messages else ""
        if "offer" in last_msg.lower() or "price" in last_msg.lower():
            return json.dumps({
                "message_type": "COUNTER_OFFER",
                "price": 205.00,
                "quantity": 100,
                "delivery_terms": "Net-30, FOB destination",
                "notes": "Competitive counter offer",
            })
        return json.dumps({
            "message_type": "ACCEPT",
            "price": 0,
            "quantity": 0,
            "delivery_terms": "",
            "notes": "Accepting terms",
        })

    async def _mock_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield mock streaming response."""
        response = self._mock_response(messages)
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
    """
    settings = get_settings()
    if provider.lower() == "groq":
        key = _resolve_api_key(settings.groq_api_key)
        if not key:
            return GeminiClient(api_key="")  # Falls through to mock
        return GroqClient(api_key=key)

    key = _resolve_api_key(settings.gemini_api_key)
    return GeminiClient(api_key=key)
