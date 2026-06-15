import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from .settings import Settings, get_settings

logger = logging.getLogger(__name__)


class BotConfigItem(BaseModel):
    """One bot entry in the shared bots credentials file."""

    bot_id: int
    token: str
    max_active_chats: int | None = None


class BotsConfigFile(BaseModel):
    bots: list[BotConfigItem] = Field(default_factory=list)


@dataclass(frozen=True)
class BotConfigEntry:
    bot_id: str
    token: str
    max_active_chats: int


def resolve_bots_config_path(settings: Settings) -> Path:
    if settings.bots_config_path.strip():
        return Path(settings.bots_config_path).expanduser().resolve()
    return (Path(__file__).resolve().parent / "bots.json").resolve()


def _load_bot_config_entries(settings: Settings) -> tuple[BotConfigEntry, ...]:
    """Read and parse the bots JSON file once per process (via get_bot_config_entries)."""
    config_path = resolve_bots_config_path(settings)
    if not config_path.is_file():
        logger.warning(
            "[Bots::_load_bot_config_entries]: Bots config file %s not found",
            config_path,
        )
        return ()

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = BotsConfigFile.model_validate(raw)
    except Exception:
        logger.exception(
            "[Bots::_load_bot_config_entries]: Invalid bots config file %s",
            config_path,
        )
        return ()

    entries: list[BotConfigEntry] = []
    for item in config.bots:
        if not item.token.strip():
            logger.warning(
                "[Bots::_load_bot_config_entries]: Skipping bot_id=%s with empty token",
                item.bot_id,
            )
            continue
        entries.append(
            BotConfigEntry(
                bot_id=str(item.bot_id),
                token=item.token.strip(),
                max_active_chats=item.max_active_chats
                if item.max_active_chats is not None
                else settings.default_max_active_chats,
            )
        )
    return tuple(entries)


@lru_cache
def get_bot_config_entries() -> tuple[BotConfigEntry, ...]:
    """Cached bot credentials — loaded once per process, like get_settings()."""
    return _load_bot_config_entries(get_settings())
