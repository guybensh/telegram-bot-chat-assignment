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
    message_provider = TelegramProvider(
        settings.telegram_api_base, mock=settings.telegram_mode == "mock"
    )
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
    """Register every bot declared in app/config/bots/*.json via the message provider."""
    if app_context.settings.telegram_mode == "mock":
        return [await app_context.bot_service.register_mock()]

    bot_config_entries = load_bot_config_entries(app_context.settings)
    if not bot_config_entries:
        logger.warning(
            "[Bootstrap: load_bots_from_config]: No bot config files found — add JSON files under app/config/bots/"
        )
        return []

    bots: list[BotRecord] = []
    for bot_config_entry in bot_config_entries:
        try:
            bot = await app_context.bot_service.register(
                bot_config_entry.token,
                app_context.message_provider,
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
