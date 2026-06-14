from abc import ABC, abstractmethod

from ..record import BotRecord


class BotRepository(ABC):
    """Data-access layer for bot profiles and their Telegram tokens."""

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
    async def get_by_token(self, token: str) -> BotRecord | None:
        """Lookup by BotFather token — used by the webhook route."""

    @abstractmethod
    async def get_token(self, bot_id: int) -> str | None:
        """Return the API token for a registered bot."""

    @abstractmethod
    async def create(self, record: BotRecord, token: str) -> BotRecord:
        """Insert or replace a bot and its token."""
