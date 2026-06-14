import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .api import TelegramAPI

logger = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    """A text message received from Telegram, parsed out of the raw update.

    This is the gateway's output contract: it carries only the facts from the
    wire. All domain processing (policy, storage, broadcast) happens elsewhere.
    """

    chat_id: int
    message_id: int
    text: str
    timestamp: datetime


class TelegramService:
    """Isolated gateway to the Telegram Bot API — pure I/O and parsing.

    It sends outgoing text, fetches updates, and parses a raw update into an
    `IncomingMessage`. It holds no reference to the chat domain and runs no
    background loop: whoever receives an update (the poller or the webhook
    route) takes the parsed message and passes it to `ChatService`.
    """

    def __init__(self, api: TelegramAPI | None = None, mock: bool = False) -> None:
        self._api = api
        self._mock = mock

    async def send(self, chat_id: int | None, text: str) -> bool:
        """Deliver text to a Telegram chat; returns whether it was delivered."""
        if self._mock:
            logger.info("Mock mode: simulating successful Telegram delivery")
            return True
        if self._api is None:
            raise RuntimeError("TelegramService has no API client configured")
        if chat_id is None:
            logger.warning("No active Telegram chat yet; cannot deliver")
            return False
        return await self._api.send_message(chat_id, text)

    async def get_updates(self, offset: int, timeout: int = 30) -> list[dict] | None:
        """Long-poll for raw updates (passthrough to the API). None on error."""
        if self._api is None:
            raise RuntimeError("TelegramService has no API client configured")
        return await self._api.get_updates(offset, timeout)

    def process_update(self, update: dict) -> IncomingMessage | None:
        """Parse a raw Telegram update into an `IncomingMessage`, or return None
        if it isn't a text message we handle. Pure function — no side effects,
        no domain knowledge."""
        payload = update.get("message") or update.get("edited_message")
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
