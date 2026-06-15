from ...config import Settings
from ...messaging_providers import ProviderBotProfile
from .record import BotRecord
from .repository import BotRepository


class BotNotFoundError(Exception):
    """Raised when the client references an unknown bot username or id."""


class BotService:
    """Bot domain — registry lookups. Tokens never appear on BotRecord."""

    def __init__(self, repository: BotRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def list_bots(self) -> list[BotRecord]:
        return await self._repository.list()

    async def get_by_username(self, username: str) -> BotRecord:
        record = await self._repository.get_by_username(username)
        if record is None:
            raise BotNotFoundError(username)
        return record

    async def get_by_id(self, bot_id: int) -> BotRecord:
        record = await self._repository.get_by_id(bot_id)
        if record is None:
            raise BotNotFoundError(str(bot_id))
        return record

    async def create(
        self,
        profile: ProviderBotProfile,
        *,
        max_chats: int | None = None,
    ) -> BotRecord:
        """Persist a bot profile resolved from the messaging provider."""
        record = BotRecord(
            bot_id=profile.bot_id,
            bot_name=profile.name,
            username=profile.username,
            max_chats=max_chats
            if max_chats is not None
            else self._settings.default_max_active_chats,
        )
        return await self._repository.create(record)

    async def register_mock(self, *, max_chats: int | None = None) -> BotRecord:
        return await self._repository.create(
            BotRecord(
                bot_id=99_000_001,
                bot_name="Mock Bot",
                username="mock_bot",
                max_chats=max_chats
                if max_chats is not None
                else self._settings.default_max_active_chats,
            )
        )
