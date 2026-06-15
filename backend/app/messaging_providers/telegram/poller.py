import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ...domain.chat import ChatService
from ...messaging_providers.types import IncomingMessage

if TYPE_CHECKING:
    from .provider import TelegramProvider

logger = logging.getLogger(__name__)

_MOCK_CHAT_ID = "10000001"


class TelegramPoller:
    """Background driver for the pull receive mechanism (getUpdates / mock feed)."""

    def __init__(
        self,
        provider: "TelegramProvider",
        chat_service: ChatService,
        *,
        bot_id: int,
    ) -> None:
        self._provider = provider
        self._chat_service = chat_service
        self._bot_id = bot_id
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
        logger.info(
            "[TelegramPoller::_poll_loop]: Telegram polling started for bot_id=%s",
            self._bot_id,
        )
        while True:
            try:
                updates = await self._provider.get_updates(
                    self._bot_id, self._offset
                )
                if updates is None:
                    await asyncio.sleep(3)
                    continue
                if updates:
                    logger.info(
                        "[TelegramPoller::_poll_loop]: Received %d update(s) via POLLING",
                        len(updates),
                    )
                for update in updates:
                    self._offset = update["update_id"] + 1
                    incoming = self._provider.parse_incoming_message(update)
                    if incoming is not None:
                        logger.info(
                            "[TelegramPoller::_poll_loop]: Update via POLLING (update_id=%s, chat=%s)",
                            update["update_id"],
                            incoming.chat_id,
                        )
                        await self._chat_service.handle_incoming(
                            self._bot_id, incoming
                        )
            except asyncio.CancelledError:
                logger.info(
                    "[TelegramPoller::_poll_loop]: Telegram polling stopped"
                )
                raise
            except Exception:
                logger.exception(
                    "[TelegramPoller::_poll_loop]: Polling iteration failed; retrying shortly"
                )
                await asyncio.sleep(3)

    async def _mock_loop(self, interval_seconds: int) -> None:
        logger.info(
            "[TelegramPoller::_mock_loop]: Mock feed started: a user message every %ss",
            interval_seconds,
        )
        counter = 0
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                counter += 1
                await self._chat_service.handle_incoming(
                    self._bot_id,
                    IncomingMessage(
                        chat_id=_MOCK_CHAT_ID,
                        message_id=counter,
                        text=f"Mock message #{counter} from the user",
                        timestamp=datetime.now(timezone.utc),
                    ),
                )
            except asyncio.CancelledError:
                logger.info("[TelegramPoller::_mock_loop]: Mock feed stopped")
                raise
            except Exception:
                logger.exception(
                    "[TelegramPoller::_mock_loop]: Mock feed iteration failed"
                )
