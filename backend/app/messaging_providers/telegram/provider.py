import logging
from datetime import datetime, timezone

from ...config import Settings, get_bot_config_entries
from ..protocol import MessageProvider, ProviderBotProfile
from ..types import IncomingMessage
from .client import TelegramClient

logger = logging.getLogger(__name__)

_MOCK_BOT_ID = "99000001"
_MOCK_TOKEN = "mock-token"


class TelegramProvider(MessageProvider):
    """Telegram implementation of MessageProvider — holds bot credentials."""

    def __init__(self, settings: Settings) -> None:
        self._mock = settings.telegram_mode == "mock"
        self._client = TelegramClient(
            settings.telegram_api_base, mock=self._mock
        )
        self._tokens: dict[str, str] = {}
        if self._mock:
            self._tokens[_MOCK_BOT_ID] = _MOCK_TOKEN
        else:
            for entry in get_bot_config_entries():
                self._tokens[entry.bot_id] = entry.token

    def has_bot(self, bot_id: str) -> bool:
        return bot_id in self._tokens

    async def fetch_bot_profile(self, bot_id: str) -> ProviderBotProfile | None:
        token = self._tokens.get(bot_id)
        if token is None:
            return None
        bot = await self._client.get_me(token)
        if not bot:
            return None
        resolved_id = str(bot["id"])
        if resolved_id != bot_id:
            logger.warning(
                "[TelegramProvider::fetch_bot_profile]: bot_id mismatch — config=%s getMe=%s",
                bot_id,
                resolved_id,
            )
            return None
        return ProviderBotProfile(
            bot_id=resolved_id,
            name=bot.get("first_name", "Telegram Bot"),
            username=bot.get("username") or f"bot{resolved_id}",
        )

    async def send_message(self, bot_id: str, chat_id: str, text: str) -> bool:
        token = self._tokens.get(bot_id)
        if token is None:
            return False
        try:
            telegram_chat_id = int(chat_id)
        except ValueError:
            logger.warning(
                "[TelegramProvider::send_message]: Invalid chat_id for Telegram: %r",
                chat_id,
            )
            return False
        return await self._client.send_message(token, telegram_chat_id, text)

    def parse_incoming_message(self, raw: dict) -> IncomingMessage | None:
        payload = raw.get("message") or raw.get("edited_message")
        if not payload:
            return None
        text = payload.get("text")
        raw_chat_id = payload.get("chat", {}).get("id")
        if text is None or raw_chat_id is None:
            return None
        return IncomingMessage(
            chat_id=str(raw_chat_id),
            message_id=payload.get("message_id"),
            text=text,
            timestamp=datetime.fromtimestamp(payload.get("date", 0), tz=timezone.utc),
        )

    async def close(self) -> None:
        await self._client.close()

    async def get_updates(
        self, bot_id: str, offset: int, timeout: int = 30
    ) -> list[dict] | None:
        token = self._tokens.get(bot_id)
        if token is None:
            return None
        return await self._client.get_updates(token, offset, timeout)

    async def set_webhook(
        self, bot_id: str, url: str, secret: str | None = None
    ) -> bool:
        token = self._tokens.get(bot_id)
        if token is None:
            return False
        return await self._client.set_webhook(token, url, secret)

    async def delete_webhook(self, bot_id: str) -> bool:
        token = self._tokens.get(bot_id)
        if token is None:
            return False
        return await self._client.delete_webhook(token)
