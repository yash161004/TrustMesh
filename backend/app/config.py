"""
TrustMesh Backend Configuration
Reads settings from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"

    # AI Provider Keys (required in production; can be empty for Phase 0 scaffold)
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./trustmesh.db"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
