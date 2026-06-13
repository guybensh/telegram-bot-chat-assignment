import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Selects which runtime configuration to load: "webhook" (the default) or
# "poll". Each layers a `.env.<APP_CONFIG>` file (the mode + its settings) on top
# of the shared `.env` (secrets like the bot token). Override per run, e.g.
#   APP_CONFIG=poll uvicorn app.main:app
APP_CONFIG = os.getenv("APP_CONFIG", "webhook")


def _env_files() -> tuple[str, ...]:
    """Env files in increasing priority: the shared `.env` first, then the
    selected `.env.<APP_CONFIG>` (so its values win on any overlap). Each name is
    resolved whether uvicorn is launched from the repo root or from backend/."""
    names = (".env", f".env.{APP_CONFIG}")
    return tuple(path for name in names for path in (name, f"../{name}"))


class Settings(BaseSettings):
    """Backend configuration.

    Resolved in priority order: real environment variables, then the per-mode
    `.env.<APP_CONFIG>` file, then the shared `.env`. `APP_CONFIG` defaults to
    "webhook"; set it to "poll" to load the polling config.
    """

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram bot token created via BotFather. Lives in the shared `.env`.
    # Required for live integration; if empty, the API runs but Telegram is off.
    telegram_bot_token: str = ""

    # How the backend handles Telegram: "webhook" (default — Telegram pushes to
    # us), "poll" (getUpdates long-poll), or "mock" (no real Telegram). Normally
    # set by the loaded `.env.<APP_CONFIG>` file.
    telegram_mode: str = "webhook"

    telegram_api_base: str = "https://api.telegram.org"

    # Maximum number of simultaneous active conversations the bot will accept.
    max_active_chats: int = 1

    # Webhook mode only. telegram_webhook_url is the PUBLIC base (e.g. an ngrok
    # https URL); the path is appended to form the registered webhook endpoint.
    telegram_webhook_url: str = ""
    telegram_webhook_path: str = "/telegram/webhook"
    telegram_webhook_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
