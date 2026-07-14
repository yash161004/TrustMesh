"""
TrustMesh LLM Client — Phase 1: Agent Logic

Provides a unified interface for calling Gemini and Groq APIs.
Supports streaming responses for real-time negotiation.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

import httpx

from .config import get_settings


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


class GeminiClient(LLMClient):
    """Google Gemini API client."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
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
                json={"contents": contents, "generationConfig": {"maxOutputTokens": 1024}},
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
        """Return a mock response when no API key is configured."""
        last_msg = messages[-1]["content"] if messages else ""
        if "offer" in last_msg.lower() or "price" in last_msg.lower():
            return json.dumps({
                "message_type": "COUNTER_OFFER",
                "price": 200.00,
                "quantity": 100,
                "delivery_terms": "Net-30, FOB origin",
                "notes": "Counter offer based on market analysis"
            })
        return json.dumps({
            "message_type": "ACCEPT",
            "price": 0,
            "quantity": 0,
            "delivery_terms": "",
            "notes": "Accepting previous terms"
        })

    async def _mock_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield mock streaming response."""
        response = self._mock_response(messages)
        words = response.split()
        for word in words:
            yield word + " "


class GroqClient(LLMClient):
    """Groq API client (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
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
                "notes": "Competitive counter offer"
            })
        return json.dumps({
            "message_type": "ACCEPT",
            "price": 0,
            "quantity": 0,
            "delivery_terms": "",
            "notes": "Accepting terms"
        })

    async def _mock_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yield mock streaming response."""
        response = self._mock_response(messages)
        words = response.split()
        for word in words:
            yield word + " "


def get_llm_client(provider: str = "gemini") -> LLMClient:
    """Factory function to get the appropriate LLM client."""
    settings = get_settings()
    if provider.lower() == "groq":
        return GroqClient(api_key=settings.groq_api_key)
    return GeminiClient(api_key=settings.gemini_api_key)
