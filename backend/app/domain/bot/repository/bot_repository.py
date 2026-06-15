from abc import ABC, abstractmethod

from ..record import BotRecord


class BotRepository(ABC):
    """Data-access layer for bot profiles."""

    @abstractmethod
    async def list(self) -> list[BotRecord]:
        """Every registered bot."""

    @abstractmethod
    async def get_by_id(self, bot_id: int) -> BotRecord | None:
        """Lookup by Telegram bot id."""

    @abstractmethod
    async def get_by_username(self, username: str) -> BotRecord | None:
        """Lookup by @username (without the @)."""

    @abstractmethod
    async def create(self, record: BotRecord) -> BotRecord:
        """Insert or replace a bot profile."""
