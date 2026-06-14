import json
import logging
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from ..config import Settings

logger = logging.getLogger(__name__)


class BotConfigFile(BaseModel):
    """Per-bot settings loaded from a JSON file in the bots config directory."""

    token: str
    max_active_chats: int | None = None


@dataclass(frozen=True)
class BotConfigEntry:
    token: str
    max_active_chats: int
    source: str


def resolve_bots_config_dir(settings: Settings) -> Path | None:
    """Find the bots config directory whether uvicorn runs from repo root or backend/."""
    for candidate in (Path(settings.bots_config_dir), Path("..") / settings.bots_config_dir):
        if candidate.is_dir():
            return candidate.resolve()
    return None


def load_bot_config_entries(settings: Settings) -> list[BotConfigEntry]:
    """Load every *.json bot config file from the configured directory."""
    config_dir = resolve_bots_config_dir(settings)
    if config_dir is None:
        logger.warning(
            "Bots config directory %r not found — add JSON files under bots/",
            settings.bots_config_dir,
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
