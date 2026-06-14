import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Selects which env overlay to load on top of `.env`. Default "production" loads
# only `.env` (webhook). Set to "development" to also load `.env.development`
# (polling). Override per run, e.g.:
#   ENVIRONMENT=development uvicorn app.main:app --reload
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")


def _env_files() -> tuple[str, ...]:
    """Env files in increasing priority: `.env` first, then `.env.development`
    when ENVIRONMENT=development (so dev values win on any overlap). Each name
    is resolved whether uvicorn is launched from the repo root or backend/."""
    names: list[str] = [".env"]
    if ENVIRONMENT == "development":
        names.append(".env.development")
    return tuple(path for name in names for path in (name, f"../{name}"))


class Settings(BaseSettings):
    """Backend configuration.

    Resolved in priority order: real environment variables, then `.env.development`
    (when ENVIRONMENT=development), then `.env`. ENVIRONMENT defaults to
    "production" (webhook); set it to "development" to load polling config.
    """

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_active_chats: int = 1

    # Telegram configuration
    telegram_api_base: str = "https://api.telegram.org"
    telegram_bot_token: str = ""
    # How the backend handles Telegram: "webhook" (default — Telegram pushes to
    # us), "poll" (getUpdates long-poll), or "mock" (no real Telegram - dev mode only).
    telegram_mode: str = "webhook"
    # Webhook mode only. telegram_webhook_url is the PUBLIC base (e.g. an ngrok
    # https URL); webhook_path + /{bot_token} form the registered endpoint.
    telegram_webhook_url: str = ""
    telegram_webhook_path: str = "/telegram/webhook"
    telegram_webhook_secret: str = ""

    # Comma-separated browser origins allowed on non-webhook API routes.
    cors_allowed_origins: list[str] = ["http://localhost:5173"]

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value  # type: ignore[return-value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
