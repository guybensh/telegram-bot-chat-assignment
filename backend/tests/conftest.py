from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from app.bootstrap import AppContext
from app.config.bots import get_bot_config_entries
from app.config.settings import Settings, get_settings
from app.connection_manager import ConnectionManager
from app.domain.bot import BotService
from app.domain.bot.repository import InMemoryBotRepository
from app.domain.chat import ChatService
from app.domain.chat.repository import InMemoryChatRepository
from app.app_factory import create_app
from app.messaging_providers import MessageProvider, ProviderBotProfile
from app.messaging_providers.telegram import TelegramProvider

from tests.fakes import FakeMessageProvider


def _clear_settings_caches() -> None:
    get_settings.cache_clear()
    get_bot_config_entries.cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings_caches_after_each_test():
    """`get_settings` / `get_bot_config_entries` use lru_cache — clear between tests."""
    yield
    _clear_settings_caches()


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    """Isolated settings: bot credentials from tmp `bots.json`."""
    _clear_settings_caches()
    bots_file = tmp_path / "bots.json"
    bots_file.write_text(
        json.dumps(
            {
                "bots": [
                    {
                        "bot_id": 123456789,
                        "token": "TEST_TOKEN_FIXTURE",
                        "max_active_chats": 2,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BOTS_CONFIG_PATH", str(bots_file))
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_URL", "")
    _clear_settings_caches()
    return get_settings()


def make_test_context(
    settings: Settings,
    message_provider: MessageProvider,
) -> AppContext:
    bot_service = BotService(InMemoryBotRepository(), settings)
    connection_manager = ConnectionManager()
    chat_repository = InMemoryChatRepository()
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


@pytest.fixture
def registered_bot() -> ProviderBotProfile:
    """Matches `bots.json` fixture bot_id in `test_settings`."""
    return ProviderBotProfile(
        bot_id="123456789",
        name="Fixture Bot",
        username="fixturebot",
    )


@pytest_asyncio.fixture
async def app_context(
    test_settings: Settings,
    registered_bot: ProviderBotProfile,
) -> AsyncIterator[tuple[AppContext, FakeMessageProvider]]:
    fake = FakeMessageProvider()
    ctx = make_test_context(test_settings, fake)
    await ctx.bot_service.create(registered_bot, max_chats=2)
    yield ctx, fake


@pytest_asyncio.fixture
async def http_client(
    app_context: tuple[AppContext, FakeMessageProvider],
):
    """Single ASGI app + shared `AppContext` for E2E (avoids duplicate `app_context`)."""
    ctx, fake = app_context
    application = create_app(ctx, lifespan=None)
    transport = httpx.ASGITransport(app=application)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    try:
        yield client, ctx, fake
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def telegram_app_context(
    test_settings: Settings,
    registered_bot: ProviderBotProfile,
) -> AsyncIterator[tuple[AppContext, TelegramProvider]]:
    """Real `TelegramProvider` (HTTP mocked via respx in tests)."""
    provider = TelegramProvider(test_settings)
    ctx = make_test_context(test_settings, provider)
    await ctx.bot_service.create(registered_bot, max_chats=2)
    try:
        yield ctx, provider
    finally:
        await provider.close()
