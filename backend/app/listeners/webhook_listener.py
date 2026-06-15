import logging

from ..bootstrap import AppContext
from ..domain.bot.record import BotRecord
from ..messaging_providers.telegram import TelegramProvider
from ..messaging_providers.telegram.utils import generate_telegram_webhook_url
from .protocol import MessageListener

logger = logging.getLogger(__name__)


class WebhookListener(MessageListener):
    """Registers Telegram webhooks per bot; delivery happens via the HTTP webhook route."""

    def __init__(self, provider: TelegramProvider) -> None:
        self._provider = provider

    async def start(self, app_context: AppContext, bots: list[BotRecord]) -> None:
        if not bots:
            logger.warning(
                "[start]: No bots registered — webhook registration skipped"
            )
            return

        settings = app_context.settings
        secret = settings.telegram_webhook_secret or None
        for bot in bots:
            url = generate_telegram_webhook_url(
                public_base_url=settings.telegram_webhook_url,
                webhook_path=settings.telegram_webhook_path,
                bot_id=bot.bot_id,
            )
            ok = await self._provider.set_webhook(bot.bot_id, url, secret)
            logger.info(
                "[start]: Webhook set for @%s (bot_id=%s) -> %s (ok=%s)",
                bot.username,
                bot.bot_id,
                url,
                ok,
            )

    async def stop(self) -> None:
        await self._provider.close()
