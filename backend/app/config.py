"""
TrustMesh Backend Configuration
Reads settings from environment variables / .env file.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4321", "http://127.0.0.1:4321"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    current_phase: str = "1 — Agent Logic"
    app_version: str = "0.2.0"

    # AI Provider Keys (required in production; can be empty for Phase 0 scaffold)
    gemini_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    llm_provider_chain: str = "groq,gemini,openrouter,mock"
    enable_calibration_anchor: bool = False

    @property
    def llm_providers(self) -> list[str]:
        return [p.strip().lower() for p in self.llm_provider_chain.split(",") if p.strip()]

    # Database
    database_url: str = "sqlite+aiosqlite:///./trustmesh.db"

    # Clerk Authentication
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_webhook_secret: str = ""

    # Rate Limiting
    rate_limit_session_create: str = "20/hour"
    rate_limit_turn: str = "100/hour"
    rate_limit_fallback: str = "500/hour"

    # CORS — stored as a raw string so pydantic-settings never tries to
    # JSON-decode it; we normalise to list in the validator below.
    allowed_origins_raw: str = ",".join(_DEFAULT_ORIGINS)

    @field_validator("allowed_origins_raw", mode="before")
    @classmethod
    def _coerce_origins(cls, v: Any) -> str:
        """Accept JSON array or comma-separated string from env."""
        if isinstance(v, list):
            return ",".join(v)
        s = str(v).strip()
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                return ",".join(parsed)
            except json.JSONDecodeError:
                pass
        return s

    @property
    def allowed_origins(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
