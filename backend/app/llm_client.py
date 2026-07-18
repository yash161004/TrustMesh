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

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

import httpx

from .config import get_settings
import logging
import re

logger = logging.getLogger(__name__)

_SECRET_PATTERNS = [
    r"(key=)[^&\s'\"]+", 
    r"(Bearer\s+)[^&\s'\"]+", 
    r"(gsk_)[a-zA-Z0-9]+", 
    r"(AIza)[a-zA-Z0-9_-]+", 
    r"(AQ\.)[a-zA-Z0-9_-]+",
    r"(sk-or-)[a-zA-Z0-9_-]+"
]

def mask_secrets(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    for pattern in _SECRET_PATTERNS:
        text = re.sub(pattern, r"\g<1>***REDACTED***", text)
    return text

class SecretMasker(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = mask_secrets(record.msg)
        if isinstance(record.args, tuple):
            new_args = []
            for arg in record.args:
                arg_str = str(arg)
                masked_str = mask_secrets(arg_str)
                if masked_str != arg_str:
                    new_args.append(masked_str)
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        return True

# Apply to root logger and specific loggers globally
logging.getLogger().addFilter(SecretMasker())
logging.getLogger("httpx").addFilter(SecretMasker())
logging.getLogger("httpcore").addFilter(SecretMasker())
logging.getLogger(__name__).addFilter(SecretMasker())

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

import time as _time
from litellm import Router
import os
from dotenv import load_dotenv
from .config import get_settings

def _get_env_key(name: str) -> str:
    key = os.environ.get(name, "")
    if _is_placeholder(key):
        return ""
    return key

# Defer router initialization until factory call so .env has time to load
_router = None

def _get_router():
    global _router
    if _router is not None:
        return _router
        
    load_dotenv()
    settings = get_settings()
    
    # Try settings first for single keys, fallback to os.environ
    groq_key = _resolve_api_key(settings.groq_api_key) or _get_env_key("GROQ_API_KEY")
    gemini_key = _resolve_api_key(settings.gemini_api_key) or _get_env_key("GEMINI_API_KEY")
    openrouter_key = _resolve_api_key(settings.openrouter_api_key) or _get_env_key("OPENROUTER_API_KEY")
    
    model_list = []
    
    # Check for multiple Groq keys (GROQ_API_KEY_1, GROQ_API_KEY_2...)
    groq_added = False
    for i in range(1, 4):
        k = _get_env_key(f"GROQ_API_KEY_{i}")
        if k:
            model_list.append({
                "model_name": "groq-voter",
                "litellm_params": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "api_key": k,
                    "rpm": 30,
                },
            })
            groq_added = True
            
    # Fallback to single GROQ_API_KEY
    if not groq_added and groq_key:
        model_list.append({
            "model_name": "groq-voter",
            "litellm_params": {
                "model": "groq/llama-3.3-70b-versatile",
                "api_key": groq_key,
                "rpm": 30,
            },
        })
        
    if gemini_key:
        model_list.append({
            "model_name": "gemini-voter",
            "litellm_params": {
                "model": "gemini/gemini-3.1-flash-lite",
                "api_key": gemini_key,
                "rpm": 60,
            },
        })
        
    if openrouter_key:
        model_list.append({
            "model_name": "openrouter-tiebreak",
            "litellm_params": {
                "model": "openrouter/google/gemma-4-26b-a4b-it:free",
                "api_key": openrouter_key,
                "rpm": 20,
                "extra_headers": {
                    "HTTP-Referer": "https://github.com/",
                    "X-Title": "TrustMesh"
                }
            },
        })
        
    _router = Router(
        model_list=model_list,
        routing_strategy="usage-based-routing-v2",
        num_retries=2,
        retry_after=1,
        allowed_fails=2,
        cooldown_time=30,
        fallbacks=[
            {"gemini-voter": ["openrouter-tiebreak"]},
            {"groq-voter": ["openrouter-tiebreak"]}
        ],
    )
    return _router

_provider_semaphores = {
    "gemini": asyncio.Semaphore(2),
    "groq": asyncio.Semaphore(2),
    "openrouter": asyncio.Semaphore(2)
}

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
# LiteLLM client
# ---------------------------------------------------------------------------

class LiteLLMClient(LLMClient):
    """LiteLLM Router client adapter."""

    def __init__(self, model_name: str, provider: str):
        self.model_name = model_name
        self.provider = provider
        
    async def generate(self, messages: list[dict], system: str = "") -> str:
        if self.model_name == "mock":
            return _mock_response_generic(messages)
            
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)
        
        semaphore = _provider_semaphores.get(self.provider)
        router = _get_router()
        
        async def _call():
            response = await router.acompletion(
                model=self.model_name,
                messages=formatted_messages,
                max_tokens=1024
            )
            self.last_used_provider = self.provider
            return response.choices[0].message.content
            
        if semaphore:
            async with semaphore:
                return await _call()
        return await _call()

    async def generate_stream(self, messages: list[dict], system: str = "") -> AsyncIterator[str]:
        if self.model_name == "mock":
            async for chunk in self._mock_stream(messages):
                yield chunk
            return
            
        formatted_messages = []
        if system:
            formatted_messages.append({"role": "system", "content": system})
        formatted_messages.extend(messages)
        
        semaphore = _provider_semaphores.get(self.provider)
        router = _get_router()
        
        async def _call_stream():
            response = await router.acompletion(
                model=self.model_name,
                messages=formatted_messages,
                max_tokens=1024,
                stream=True
            )
            self.last_used_provider = self.provider
            async for chunk in response:
                if hasattr(chunk.choices[0], "delta") and hasattr(chunk.choices[0].delta, "content"):
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        yield delta_content
                    
        if semaphore:
            async with semaphore:
                async for chunk in _call_stream():
                    yield chunk
        else:
            async for chunk in _call_stream():
                yield chunk
                
    async def _mock_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        response = _mock_response_generic(messages)
        words = response.split()
        for word in words:
            yield word + " "


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_llm_client(provider: str = None) -> LLMClient:
    """Factory function to get the appropriate LLM client."""
    settings = get_settings()
    
    if provider == "groq":
        key = _resolve_api_key(settings.groq_api_key)
        return LiteLLMClient("groq-voter", "groq") if key else LiteLLMClient("mock", "mock")
        
    elif provider == "gemini":
        key = _resolve_api_key(settings.gemini_api_key)
        return LiteLLMClient("gemini-voter", "gemini") if key else LiteLLMClient("mock", "mock")
        
    elif provider == "openrouter":
        key = _resolve_api_key(settings.openrouter_api_key)
        return LiteLLMClient("openrouter-tiebreak", "openrouter") if key else LiteLLMClient("mock", "mock")
        
    elif provider == "mock":
        return LiteLLMClient("mock", "mock")
        
    # Default behavior if no specific provider requested
    key = _resolve_api_key(settings.gemini_api_key)
    if key:
        return LiteLLMClient("gemini-voter", "gemini")
        
    key = _resolve_api_key(settings.groq_api_key)
    if key:
        return LiteLLMClient("groq-voter", "groq")
        
    key = _resolve_api_key(settings.openrouter_api_key)
    if key:
        return LiteLLMClient("openrouter-tiebreak", "openrouter")
        
    return LiteLLMClient("mock", "mock")
