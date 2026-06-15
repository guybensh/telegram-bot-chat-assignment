import logging

from ..bootstrap import AppContext
from ..domain.bot.record import BotRecord
from ..messaging_providers.telegram import TelegramProvider
from ..messaging_providers.telegram.poller import TelegramPoller
from .protocol import MessageListener

logger = logging.getLogger(__name__)


class MockListener(MessageListener):
    """Dev-only simulated incoming messages. To be reworked in a later cleanup."""

    def __init__(self, provider: TelegramProvider) -> None:
        self._provider = provider
        self._poller: TelegramPoller | None = None

    async def start(self, app_context: AppContext, bots: list[BotRecord]) -> None:
        if not bots:
            return
        bot = bots[0]
        logger.info(
            "[start]: Mock mode: simulated incoming message every 10s"
        )
        self._poller = TelegramPoller(
            self._provider,
            app_context.chat_service,
            bot_id=bot.bot_id,
        )
        await self._poller.start_mock_feed()

    async def stop(self) -> None:
        if self._poller is not None:
            await self._poller.stop()
            self._poller = None
        await self._provider.close()
