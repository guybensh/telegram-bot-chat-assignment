import asyncio

from ..record import BotRecord
from .bot_repository import BotRepository


class InMemoryBotRepository(BotRepository):
    """In-memory bot registry. Swappable for a DB implementation later."""

    def __init__(self) -> None:
        self._by_id: dict[int, BotRecord] = {}
        self._by_username: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def list(self) -> list[BotRecord]:
        async with self._lock:
            return list(self._by_id.values())

    async def get_by_id(self, bot_id: int) -> BotRecord | None:
        async with self._lock:
            return self._by_id.get(bot_id)

    async def get_by_username(self, username: str) -> BotRecord | None:
        async with self._lock:
            bot_id = self._by_username.get(username.lower())
            return self._by_id.get(bot_id) if bot_id is not None else None

    async def create(self, record: BotRecord) -> BotRecord:
        async with self._lock:
            self._by_id[record.bot_id] = record
            self._by_username[record.username.lower()] = record.bot_id
            return record
