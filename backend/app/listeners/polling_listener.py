import logging

from ..bootstrap import AppContext
from ..domain.bot.record import BotRecord
from ..messaging_providers.telegram import TelegramProvider
from ..messaging_providers.telegram.poller import TelegramPoller
from .protocol import MessageListener

logger = logging.getLogger(__name__)


class PollingListener(MessageListener):
    """Long-polls Telegram getUpdates per bot and forwards messages to ChatService."""

    def __init__(self, provider: TelegramProvider) -> None:
        self._provider = provider
        self._pollers: list[TelegramPoller] = []

    async def start(self, app_context: AppContext, bots: list[BotRecord]) -> None:
        if not bots:
            logger.warning("No bots registered — polling disabled")
            return

        for bot in bots:
            token = await app_context.bot_service.get_token(bot.username)
            await self._provider.delete_webhook(token)
            poller = TelegramPoller(
                self._provider,
                app_context.chat_service,
                bot_id=bot.bot_id,
                token=token,
            )
            self._pollers.append(poller)
            await poller.start_polling()
            logger.info("Polling started for @%s", bot.username)

    async def stop(self) -> None:
        for poller in self._pollers:
            await poller.stop()
        self._pollers.clear()
        await self._provider.close()
