import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from .telegram_api import TelegramAPI

logger = logging.getLogger(__name__)

# Fixed chat id used by the mock feed so its messages bind to (and stay on) a
# single simulated participant, exactly like a real chat would.
_MOCK_CHAT_ID = 10_000_001


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


# Async callback the gateway invokes for each incoming message. The owner
# (ChatService) registers it via set_handler — the gateway never learns what it
# does with the message.
IncomingHandler = Callable[[IncomingMessage], Awaitable[None]]


class TelegramService:
    """Isolated gateway to the Telegram Bot API.

    Its only concerns are talking to Telegram: delivering outgoing text, and
    receiving updates (by polling or via the webhook route), parsing them into
    `IncomingMessage`, and handing them to the registered handler. It holds no
    message store, no WebSocket clients, and no single-chat policy — those are
    domain decisions that belong to ChatService.
    """

    def __init__(self, api: TelegramAPI, mock: bool = False) -> None:
        self._api = api
        # Mock mode never touches the real API: outgoing sends are simulated as
        # delivered, so the app can be tested end-to-end without a live bot.
        self._mock = mock
        self._handler: IncomingHandler | None = None
        self._poll_task: asyncio.Task | None = None
        self._offset = 0

    def set_handler(self, handler: IncomingHandler) -> None:
        self._handler = handler

    # --- outgoing --------------------------------------------------------

    async def send(self, chat_id: int | None, text: str) -> bool:
        """Deliver text to a Telegram chat; returns whether it was delivered.

        A missing chat_id (no participant has messaged the bot yet) is a
        delivery failure. Mock mode always reports success without any network
        call.
        """
        if self._mock:
            logger.info("Mock mode: simulating successful Telegram delivery")
            return True
        if chat_id is None:
            logger.warning("No active Telegram chat yet; cannot deliver")
            return False
        return await self._api.send_message(chat_id, text)

    # --- incoming --------------------------------------------------------

    async def process_update(self, update: dict) -> None:
        """Parse one raw Telegram update and forward any text message to the
        registered handler. Called by both the poller and the webhook route."""
        payload = update.get("message") or update.get("edited_message")
        if not payload:
            return
        text = payload.get("text")
        chat_id = payload.get("chat", {}).get("id")
        if text is None or chat_id is None:
            return  # ignore non-text messages and malformed updates

        if self._handler is None:
            logger.warning("No incoming handler registered; dropping update")
            return

        await self._handler(
            IncomingMessage(
                chat_id=chat_id,
                message_id=payload.get("message_id"),
                text=text,
                timestamp=datetime.fromtimestamp(
                    payload.get("date", 0), tz=timezone.utc
                ),
            )
        )

    # --- mock receive strategy ------------------------------------------

    async def start_mock_feed(self, interval_seconds: int = 10) -> None:
        """Mock mode only: synthesize an incoming bot message on a fixed
        interval, pushed through the same handler as a real update. Lets the
        incoming flow be demoed live without a Telegram bot."""
        self._poll_task = asyncio.create_task(self._mock_loop(interval_seconds))

    async def _mock_loop(self, interval_seconds: int) -> None:
        logger.info("Mock feed started: a bot message every %ss", interval_seconds)
        counter = 0
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                counter += 1
                if self._handler is None:
                    continue
                await self._handler(
                    IncomingMessage(
                        chat_id=_MOCK_CHAT_ID,
                        message_id=counter,
                        text=f"Mock message #{counter} from the user",
                        timestamp=datetime.now(timezone.utc),
                    )
                )
            except asyncio.CancelledError:
                logger.info("Mock feed stopped")
                raise
            except Exception:
                logger.exception("Mock feed iteration failed")

    # --- polling strategy ------------------------------------------------

    async def start_polling(self) -> None:
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop_polling(self) -> None:
        if self._poll_task is None:
            return
        self._poll_task.cancel()
        try:
            await self._poll_task
        except asyncio.CancelledError:
            pass

    async def _poll_loop(self) -> None:
        logger.info("Telegram polling started")
        while True:
            try:
                updates = await self._api.get_updates(self._offset)
                if updates is None:
                    # Error (e.g. 409 Conflict — another poller is active).
                    # Back off so we don't hammer the API.
                    await asyncio.sleep(3)
                    continue
                for update in updates:
                    self._offset = update["update_id"] + 1
                    await self.process_update(update)
            except asyncio.CancelledError:
                logger.info("Telegram polling stopped")
                raise
            except Exception:
                logger.exception("Polling iteration failed; retrying shortly")
                await asyncio.sleep(3)
