import logging
from dataclasses import dataclass

from .config import Settings, get_settings, load_bot_config_entries
from .connection_manager import ConnectionManager
from .domain.bot import BotService
from .domain.bot.bot_service import BotRegistrationError
from .domain.bot.record import BotRecord
from .domain.bot.repository import InMemoryBotRepository
from .domain.chat import ChatService
from .domain.chat.repository import InMemoryChatRepository
from .logging_setup import configure_logging
from .messaging_providers import MessageProvider
from .messaging_providers.telegram import TelegramProvider
from .messaging_providers.telegram.poller import TelegramPoller
from .messaging_providers.telegram.utils import generate_telegram_webhook_url

logger = logging.getLogger(__name__)

_deps: "Dependencies | None" = None


@dataclass
class Dependencies:
    settings: Settings
    bot_service: BotService
    chat: ChatService
    message_provider: MessageProvider
    telegram_runtime: "TelegramReceiveRuntime"
    connection_manager: ConnectionManager


def get_deps() -> Dependencies:
    if _deps is None:
        raise RuntimeError("Dependencies not initialized — call build_dependencies() first")
    return _deps


def build_dependencies() -> Dependencies:
    global _deps

    settings = get_settings()
    configure_logging(settings)

    bot_service = BotService(InMemoryBotRepository(), settings)
    connection_manager = ConnectionManager()
    chat_repository = InMemoryChatRepository()
    message_provider = TelegramProvider(
        settings.telegram_api_base, mock=settings.telegram_mode == "mock"
    )
    chat = ChatService(
        chat_repository, connection_manager, message_provider, bot_service
    )
    telegram_runtime = TelegramReceiveRuntime(
        settings, message_provider, chat, bot_service
    )

    _deps = Dependencies(
        settings=settings,
        bot_service=bot_service,
        chat=chat,
        message_provider=message_provider,
        telegram_runtime=telegram_runtime,
        connection_manager=connection_manager,
    )
    return _deps


async def load_bots_from_config(
    settings: Settings,
    bot_service: BotService,
    provider: MessageProvider,
) -> list[BotRecord]:
    """Register every bot declared in app/config/bots/*.json via the message provider."""
    if settings.telegram_mode == "mock":
        return [await bot_service.register_mock()]

    bot_config_entries = load_bot_config_entries(settings)
    if not bot_config_entries:
        logger.warning(
            "No bot config files found — add JSON files under app/config/bots/"
        )
        return []

    bots: list[BotRecord] = []
    for bot_config_entry in bot_config_entries:
        try:
            bot = await bot_service.register(
                bot_config_entry.token,
                provider,
                max_chats=bot_config_entry.max_active_chats,
            )
            bots.append(bot)
            logger.info(
                "Loaded bot @%s from %s (max_active_chats=%s)",
                bot.username,
                bot_config_entry.source,
                bot.max_chats,
            )
        except BotRegistrationError:
            logger.exception(
                "Skipping bot from %s — getMe failed for token prefix %s",
                bot_config_entry.source,
                bot_config_entry.token.split(":", 1)[0],
            )
    return bots


class TelegramReceiveRuntime:
    """Starts and stops webhook registration or polling for registered bots."""

    def __init__(
        self,
        settings: Settings,
        provider: TelegramProvider,
        chat: ChatService,
        bot_service: BotService,
    ) -> None:
        self._settings = settings
        self._provider = provider
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
        await self._provider.close()

    async def _start_mock(self, bot: BotRecord) -> None:
        logger.info("Mock mode: simulated incoming message every 10s")
        poller = TelegramPoller(
            self._provider,
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
        ok = await self._provider.set_webhook(
            token, url, self._settings.telegram_webhook_secret or None
        )
        safe_url = url.replace(token, "<token>")
        logger.info("Webhook set for @%s (%s) -> ok=%s", bot.username, safe_url, ok)

    async def _start_polling(self, bot: BotRecord) -> TelegramPoller:
        token = await self._bot_service.get_token(bot.username)
        await self._provider.delete_webhook(token)
        poller = TelegramPoller(
            self._provider,
            self._chat,
            bot_id=bot.bot_id,
            token=token,
        )
        await poller.start_polling()
        logger.info("Polling started for @%s", bot.username)
        return poller
