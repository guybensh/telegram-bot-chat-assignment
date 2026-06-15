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
            logger.warning("No bots registered — webhook registration skipped")
            return

        settings = app_context.settings
        secret = settings.telegram_webhook_secret or None
        for bot in bots:
            token = await app_context.bot_service.get_token(bot.username)
            url = generate_telegram_webhook_url(
                public_base_url=settings.telegram_webhook_url,
                webhook_path=settings.telegram_webhook_path,
                bot_token=token,
            )
            ok = await self._provider.set_webhook(token, url, secret)
            safe_url = url.replace(token, "<token>")
            logger.info(
                "Webhook set for @%s (%s) -> ok=%s", bot.username, safe_url, ok
            )

    async def stop(self) -> None:
        await self._provider.close()
