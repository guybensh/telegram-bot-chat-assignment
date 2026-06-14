from dataclasses import dataclass

from .domain.bot import BotService
from .domain.bot.bootstrap import TelegramReceiveRuntime
from .domain.bot.repository import InMemoryBotRepository
from .domain.chat import ChatService
from .domain.chat.repository import InMemoryChatRepository
from config import Settings, get_settings
from .connection_manager import ConnectionManager
from .logging_setup import configure_logging
from .messaging_providers.telegram import TelegramGateway, TelegramService

_deps: "Dependencies | None" = None


@dataclass
class Dependencies:
    settings: Settings
    bot_service: BotService
    chat: ChatService
    telegram_gateway: TelegramGateway
    telegram_parser: TelegramService
    telegram_runtime: TelegramReceiveRuntime
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
    telegram_gateway = TelegramGateway(
        settings.telegram_api_base, mock=settings.telegram_mode == "mock"
    )
    telegram_parser = TelegramService(api=None, mock=True)
    chat = ChatService(
        chat_repository, connection_manager, telegram_gateway, bot_service
    )
    telegram_runtime = TelegramReceiveRuntime(
        settings, telegram_gateway, telegram_parser, chat, bot_service
    )

    _deps = Dependencies(
        settings=settings,
        bot_service=bot_service,
        chat=chat,
        telegram_gateway=telegram_gateway,
        telegram_parser=telegram_parser,
        telegram_runtime=telegram_runtime,
        connection_manager=connection_manager,
    )
    return _deps
