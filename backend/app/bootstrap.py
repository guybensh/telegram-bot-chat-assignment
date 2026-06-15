import logging
from dataclasses import dataclass

from .config import Settings, get_settings, get_bot_config_entries
from .connection_manager import ConnectionManager
from .domain.bot import BotService
from .domain.bot.record import BotRecord
from .domain.bot.repository import InMemoryBotRepository
from .domain.chat import ChatService
from .domain.chat.repository import InMemoryChatRepository
from .logging_setup import configure_logging
from .messaging_providers import MessageProvider
from .messaging_providers.telegram import TelegramProvider

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    settings: Settings
    bot_service: BotService
    chat_service: ChatService
    message_provider: MessageProvider
    connection_manager: ConnectionManager


def build_app_context() -> AppContext:
    settings = get_settings()
    configure_logging(settings)

    bot_service = BotService(InMemoryBotRepository(), settings)
    connection_manager = ConnectionManager()
    chat_repository = InMemoryChatRepository()
    message_provider = TelegramProvider(settings)
    chat_service = ChatService(
        chat_repository, connection_manager, message_provider, bot_service
    )

    return AppContext(
        settings=settings,
        bot_service=bot_service,
        chat_service=chat_service,
        message_provider=message_provider,
        connection_manager=connection_manager,
    )


async def load_bots_from_config(app_context: AppContext) -> list[BotRecord]:
    """Register every bot declared in the bots JSON file via the message provider."""
    logger.info("[load_bots_from_config]: Attempt loading")

    if app_context.settings.telegram_mode == "mock":
        return [await app_context.bot_service.register_mock()]

    provider = app_context.message_provider
    if not isinstance(provider, TelegramProvider):
        raise TypeError("load_bots_from_config requires TelegramProvider")

    bot_config_entries = get_bot_config_entries()
    if not bot_config_entries:
        logger.warning(
            "[load_bots_from_config]: No bots configured — add backend/app/config/bots.json"
        )
        return []

    bots: list[BotRecord] = []
    for entry in bot_config_entries:
        profile = await provider.fetch_bot_profile(entry.bot_id)
        if profile is None:
            logger.error(
                "[load_bots_from_config]: Skipping bot_id=%s — getMe failed or id mismatch",
                entry.bot_id,
            )
            continue
        bot = await app_context.bot_service.create(
            profile, max_chats=entry.max_active_chats
        )
        bots.append(bot)
        logger.info(
            "[load_bots_from_config]: Loaded bot @%s (bot_id=%s, max_active_chats=%s)",
            bot.username,
            bot.bot_id,
            bot.max_chats,
        )
    return bots
