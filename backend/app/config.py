import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")


def _env_files() -> tuple[str, ...]:
    names: list[str] = [".env"]
    if ENVIRONMENT == "development":
        names.append(".env.development")
    return tuple(path for name in names for path in (name, f"../{name}"))


class Settings(BaseSettings):
    """General app configuration (.env). Bot tokens live in bots/*.json files."""

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Default max active conversations when a bot JSON file omits max_active_chats.
    default_max_active_chats: int = 10

    # Directory of per-bot JSON configs (token + max_active_chats), repo-relative.
    bots_config_dir: str = "bots"

    telegram_api_base: str = "https://api.telegram.org"
    telegram_mode: str = "webhook"
    telegram_webhook_url: str = ""
    telegram_webhook_path: str = "/telegram/webhook"
    telegram_webhook_secret: str = ""

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
