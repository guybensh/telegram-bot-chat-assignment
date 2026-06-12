import asyncio
import logging
from datetime import datetime, timezone

from .chat import ChatService
from .telegram_service import IncomingMessage, TelegramService

logger = logging.getLogger(__name__)

# Fixed chat id used by the mock feed so its messages bind to (and stay on) a
# single simulated participant, exactly like a real chat would.
_MOCK_CHAT_ID = 10_000_001


class TelegramReceiver:
    """Drives incoming Telegram updates into the chat domain.

    It owns the background receive loop (real polling, or the mock feed), asks
    the gateway to parse each update, and passes every parsed `IncomingMessage`
    to `ChatService.handle_incoming`. This is the single place that wires the
    gateway to the domain for the receive direction — the webhook route plays
    the same role for webhook mode. The gateway itself stays domain-agnostic.
    """

    def __init__(self, telegram: TelegramService, chat: ChatService) -> None:
        self._telegram = telegram
        self._chat = chat
        self._task: asyncio.Task | None = None
        self._offset = 0

    async def start_polling(self) -> None:
        self._task = asyncio.create_task(self._poll_loop())

    async def start_mock_feed(self, interval_seconds: int = 10) -> None:
        self._task = asyncio.create_task(self._mock_loop(interval_seconds))

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _poll_loop(self) -> None:
        logger.info("Telegram polling started")
        while True:
            try:
                updates = await self._telegram.get_updates(self._offset)
                if updates is None:
                    # Error (e.g. 409 Conflict — another poller is active).
                    # Back off so we don't hammer the API.
                    await asyncio.sleep(3)
                    continue
                for update in updates:
                    self._offset = update["update_id"] + 1
                    incoming = self._telegram.process_update(update)
                    if incoming is not None:
                        await self._chat.handle_incoming(incoming)
            except asyncio.CancelledError:
                logger.info("Telegram polling stopped")
                raise
            except Exception:
                logger.exception("Polling iteration failed; retrying shortly")
                await asyncio.sleep(3)

    async def _mock_loop(self, interval_seconds: int) -> None:
        logger.info("Mock feed started: a user message every %ss", interval_seconds)
        counter = 0
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                counter += 1
                await self._chat.handle_incoming(
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
