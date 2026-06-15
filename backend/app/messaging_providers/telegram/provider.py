from datetime import datetime, timezone

from ..protocol import MessageProvider, ProviderBotProfile
from ..types import IncomingMessage
from .client import TelegramClient


class TelegramProvider(MessageProvider):
    """Telegram implementation of MessageProvider."""

    def __init__(self, api_base: str, *, mock: bool = False) -> None:
        self._client = TelegramClient(api_base, mock=mock)

    async def resolve_bot(self, credentials: str) -> ProviderBotProfile | None:
        bot = await self._client.get_me(credentials)
        if not bot:
            return None
        bot_id = bot["id"]
        return ProviderBotProfile(
            bot_id=bot_id,
            name=bot.get("first_name", "Telegram Bot"),
            username=bot.get("username") or f"bot{bot_id}",
        )

    async def send_message(self, credentials: str, chat_id: int, text: str) -> bool:
        return await self._client.send_message(credentials, chat_id, text)

    def parse_incoming_message(self, raw: dict) -> IncomingMessage | None:
        payload = raw.get("message") or raw.get("edited_message")
        if not payload:
            return None
        text = payload.get("text")
        chat_id = payload.get("chat", {}).get("id")
        if text is None or chat_id is None:
            return None
        return IncomingMessage(
            chat_id=chat_id,
            message_id=payload.get("message_id"),
            text=text,
            timestamp=datetime.fromtimestamp(payload.get("date", 0), tz=timezone.utc),
        )

    async def close(self) -> None:
        await self._client.close()

    async def get_updates(
        self, credentials: str, offset: int, timeout: int = 30
    ) -> list[dict] | None:
        return await self._client.get_updates(credentials, offset, timeout)

    async def set_webhook(
        self, credentials: str, url: str, secret: str | None = None
    ) -> bool:
        return await self._client.set_webhook(credentials, url, secret)

    async def delete_webhook(self, credentials: str) -> bool:
        return await self._client.delete_webhook(credentials)
