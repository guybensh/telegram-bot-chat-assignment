from __future__ import annotations

from app.messaging_providers import IncomingMessage, MessageProvider, ProviderBotProfile


class FakeMessageProvider(MessageProvider):
    """Test double for Telegram — no network."""

    def __init__(self, *, send_succeeds: bool = True) -> None:
        self.send_succeeds = send_succeeds
        self.sent: list[tuple[str, str, str]] = []

    async def fetch_bot_profile(self, bot_id: str) -> ProviderBotProfile | None:
        return ProviderBotProfile(
            bot_id=bot_id,
            name="Fixture Bot",
            username=f"bot_{bot_id}",
        )

    async def send_message(self, bot_id: str, chat_id: str, text: str) -> bool:
        self.sent.append((bot_id, chat_id, text))
        return self.send_succeeds

    def parse_incoming_message(self, raw: dict) -> IncomingMessage | None:
        return self._default_parse(raw)

    @staticmethod
    def _default_parse(raw: dict) -> IncomingMessage | None:
        from datetime import datetime, timezone

        payload = raw.get("message") or raw.get("edited_message")
        if not payload:
            return None
        text = payload.get("text")
        raw_chat_id = payload.get("chat", {}).get("id")
        if text is None or raw_chat_id is None:
            return None
        return IncomingMessage(
            chat_id=str(raw_chat_id),
            message_id=int(payload.get("message_id", 0)),
            text=str(text),
            timestamp=datetime.fromtimestamp(
                int(payload.get("date", 0)), tz=timezone.utc
            ),
        )

    async def close(self) -> None:
        return None
