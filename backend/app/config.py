"""Centralized configuration via pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # API keys
    ANTHROPIC_API_KEY: str
    EXA_API_KEY: str
    VOYAGE_API_KEY: str

    # Auth (Clerk)
    CLERK_ISSUER: str = ""  # e.g., https://your-app.clerk.accounts.dev
    CLERK_SECRET_KEY: str = ""

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "dev-secret"

    # LLM defaults
    CLAUDE_MODEL: str = "claude-opus-4-7"
    CLAUDE_MAX_TOKENS: int = 8000

    # Workflow timeouts in seconds
    SCRAPE_TIMEOUT: int = 60
    LLM_TIMEOUT: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
