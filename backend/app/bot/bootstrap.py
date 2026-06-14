import logging

from ..config import Settings
from ..chat import ChatService
from ..messaging_providers.telegram import TelegramGateway, TelegramService
from ..messaging_providers.telegram.poller import TelegramPoller
from ..messaging_providers.telegram.utils import generate_telegram_webhook_url
from .bot_service import BotRegistrationError, BotService
from .config_loader import load_bot_config_entries
from .record import BotRecord

logger = logging.getLogger(__name__)


async def load_bots_from_config(
    settings: Settings,
    bot_service: BotService,
    gateway: TelegramGateway,
) -> list[BotRecord]:
    """Register every bot declared in bots/*.json via Telegram getMe."""
    if settings.telegram_mode == "mock":
        return [await bot_service.register_mock()]

    entries = load_bot_config_entries(settings)
    if not entries:
        logger.warning("No bot config files found — add JSON files under bots/")
        return []

    bots: list[BotRecord] = []
    for entry in entries:
        try:
            bot = await bot_service.register_from_token(
                entry.token,
                gateway,
                max_chats=entry.max_active_chats,
            )
            bots.append(bot)
            logger.info(
                "Loaded bot @%s from %s (max_active_chats=%s)",
                bot.username,
                entry.source,
                bot.max_chats,
            )
        except BotRegistrationError:
            logger.exception(
                "Skipping bot from %s — getMe failed for token prefix %s",
                entry.source,
                entry.token.split(":", 1)[0],
            )
    return bots


class TelegramReceiveRuntime:
    """Starts and stops webhook registration or polling for registered bots."""

    def __init__(
        self,
        settings: Settings,
        gateway: TelegramGateway,
        parser: TelegramService,
        chat: ChatService,
        bot_service: BotService,
    ) -> None:
        self._settings = settings
        self._gateway = gateway
        self._parser = parser
        self._chat = chat
        self._bot_service = bot_service
        self._pollers: list[TelegramPoller] = []

    async def start(self, bots: list[BotRecord]) -> None:
        if self._settings.telegram_mode == "mock":
            if bots:
                await self._start_mock(bots[0])
            return

        if not bots:
            logger.warning("No bots registered — Telegram receive disabled")
            return

        if self._settings.telegram_mode == "webhook":
            for bot in bots:
                await self._start_webhook(bot)
            return

        for bot in bots:
            self._pollers.append(await self._start_polling(bot))

    async def stop(self) -> None:
        for poller in self._pollers:
            await poller.stop()
        self._pollers.clear()
        await self._gateway.close()

    async def _start_mock(self, bot: BotRecord) -> None:
        logger.info("Mock mode: simulated incoming message every 10s")
        poller = TelegramPoller(
            self._gateway,
            self._parser,
            self._chat,
            bot_id=bot.bot_id,
            token=await self._bot_service.get_token(bot.username),
        )
        self._pollers.append(poller)
        await poller.start_mock_feed()

    async def _start_webhook(self, bot: BotRecord) -> None:
        token = await self._bot_service.get_token(bot.username)
        url = generate_telegram_webhook_url(
            public_base_url=self._settings.telegram_webhook_url,
            webhook_path=self._settings.telegram_webhook_path,
            bot_token=token,
        )
        ok = await self._gateway.set_webhook(
            token, url, self._settings.telegram_webhook_secret or None
        )
        safe_url = url.replace(token, "<token>")
        logger.info("Webhook set for @%s (%s) -> ok=%s", bot.username, safe_url, ok)

    async def _start_polling(self, bot: BotRecord) -> TelegramPoller:
        token = await self._bot_service.get_token(bot.username)
        await self._gateway.delete_webhook(token)
        poller = TelegramPoller(
            self._gateway,
            self._parser,
            self._chat,
            bot_id=bot.bot_id,
            token=token,
        )
        await poller.start_polling()
        logger.info("Polling started for @%s", bot.username)
        return poller
