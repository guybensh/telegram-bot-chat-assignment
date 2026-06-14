import json
import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from .settings import Settings

logger = logging.getLogger(__name__)


class BotConfigFile(BaseModel):
    """Per-bot settings loaded from a JSON file in backend/config/bots/."""

    token: str
    max_active_chats: int | None = None


@dataclass(frozen=True)
class BotConfigEntry:
    token: str
    max_active_chats: int
    source: str


def _backend_root() -> Path:
    # backend/config/bots.py -> backend/
    return Path(__file__).resolve().parents[1]


def resolve_bots_config_dir() -> Path:
    """Return backend/config/bots/."""
    return (_backend_root() / "config" / "bots").resolve()


def load_bot_config_entries(settings: Settings) -> list[BotConfigEntry]:
    """Load every *.json bot config file from backend/config/bots/."""
    config_dir = resolve_bots_config_dir()
    if not config_dir.is_dir():
        logger.warning(
            "Bots config directory %s not found — add JSON files under backend/config/bots/",
            config_dir,
        )
        return []

    entries: list[BotConfigEntry] = []
    for path in sorted(config_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            config = BotConfigFile.model_validate(raw)
            if not config.token.strip():
                logger.warning("Skipping empty token in %s", path.name)
                continue
            entries.append(
                BotConfigEntry(
                    token=config.token.strip(),
                    max_active_chats=config.max_active_chats
                    if config.max_active_chats is not None
                    else settings.default_max_active_chats,
                    source=path.name,
                )
            )
        except Exception:
            logger.exception("Invalid bot config file %s", path.name)
    return entries
