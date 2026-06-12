from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration, read from environment variables (or a local .env).

    docker-compose injects these; for a bare `uvicorn` run they are read from
    `.env` in the backend dir or `../.env` at the repo root (see .env.example).
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram bot token created via BotFather. Required for live integration;
    # if empty, the API still runs but Telegram delivery is disabled.
    telegram_bot_token: str = ""

    # How the backend handles Telegram: "poll" (getUpdates, no public URL needed
    # — ideal for local dev), "webhook" (Telegram pushes to us), or "mock"
    # (no real Telegram at all; outgoing sends are simulated for local testing).
    telegram_mode: str = "poll"

    telegram_api_base: str = "https://api.telegram.org"

    # Maximum number of simultaneous active conversations the bot will accept.
    # 1 keeps the assignment's single-participant behavior; raise it (env
    # MAX_ACTIVE_CHATS) to let the back-office handle several users at once.
    max_active_chats: int = 1

    # Webhook mode only. telegram_webhook_url is the PUBLIC base (e.g. an ngrok
    # https URL); the path is appended to form the registered webhook endpoint.
    telegram_webhook_url: str = ""
    telegram_webhook_path: str = "/telegram/webhook"
    telegram_webhook_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
