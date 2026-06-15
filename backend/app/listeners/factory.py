from ..bootstrap import AppContext
from ..messaging_providers.telegram import TelegramProvider
from .mock_listener import MockListener
from .polling_listener import PollingListener
from .protocol import MessageListener
from .webhook_listener import WebhookListener


def create_listeners(app_context: AppContext) -> list[MessageListener]:
    """Pick incoming-message listeners from TELEGRAM_MODE in settings."""
    provider = app_context.message_provider
    if not isinstance(provider, TelegramProvider):
        raise TypeError("Listener factory requires TelegramProvider")

    mode = app_context.settings.telegram_mode
    if mode == "webhook":
        return [WebhookListener(provider)]
    if mode == "poll":
        return [PollingListener(provider)]
    if mode == "mock":
        return [MockListener(provider)]
    raise ValueError(f"Unknown TELEGRAM_MODE: {mode!r}")
