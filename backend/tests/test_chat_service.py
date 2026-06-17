from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.bot import BotNotFoundError
from app.domain.chat import ChatService, NoActiveConversationError
from app.messaging_providers import IncomingMessage, ProviderBotProfile

from tests.conftest import make_test_context
from tests.fakes import FakeMessageProvider


@pytest.fixture
def chat_service(test_settings) -> ChatService:
    fake = FakeMessageProvider()
    ctx = make_test_context(test_settings, fake)
    return ctx.chat_service


@pytest.fixture
async def chat_service_with_bot(test_settings) -> ChatService:
    fake = FakeMessageProvider()
    ctx = make_test_context(test_settings, fake)
    await ctx.bot_service.create(
        ProviderBotProfile(
            bot_id="123456789",
            name="Fixture",
            username="fixturebot",
        ),
        max_chats=2,
    )
    return ctx.chat_service


@pytest.mark.asyncio
async def test_list_chat_summaries_bot_not_found(chat_service: ChatService):
    with pytest.raises(BotNotFoundError):
        await chat_service.list_chat_summaries("missing")


@pytest.mark.asyncio
async def test_list_messages_bot_not_found(chat_service_with_bot: ChatService):
    with pytest.raises(BotNotFoundError):
        await chat_service_with_bot.list_messages("nobody", "1")


@pytest.mark.asyncio
async def test_send_no_active_chat_raises(chat_service_with_bot: ChatService):
    with pytest.raises(NoActiveConversationError):
        await chat_service_with_bot.send_message(
            "fixturebot",
            "msg-1",
            "111",
            "hello",
            datetime.now(timezone.utc),
        )


@pytest.mark.asyncio
async def test_send_sunny_path(chat_service_with_bot: ChatService):
    await chat_service_with_bot.handle_incoming_message(
        "123456789",
        IncomingMessage(
            chat_id="42",
            message_id=1,
            text="user hi",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )
    out = await chat_service_with_bot.send_message(
        "fixturebot",
        "out-1",
        "42",
        "agent reply",
        datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    assert out.status.value == "sent"
    assert out.sender.value == "agent"
    history = await chat_service_with_bot.list_messages("fixturebot", "42")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_send_telegram_failure_marks_failed(test_settings):
    failing = FakeMessageProvider(send_succeeds=False)
    ctx = make_test_context(test_settings, failing)
    await ctx.bot_service.create(
        ProviderBotProfile(
            bot_id="123456789",
            name="Fixture",
            username="fixturebot",
        ),
        max_chats=2,
    )
    await ctx.chat_service.handle_incoming_message(
        "123456789",
        IncomingMessage(
            chat_id="7",
            message_id=1,
            text="x",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )
    out = await ctx.chat_service.send_message(
        "fixturebot",
        "f1",
        "7",
        "will fail",
        datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    assert out.status.value == "failed"
    assert failing.sent == [("123456789", "7", "will fail")]


@pytest.mark.asyncio
async def test_mark_read_inactive_raises(chat_service_with_bot: ChatService):
    with pytest.raises(NoActiveConversationError):
        await chat_service_with_bot.mark_message_read(
            "fixturebot",
            "no-such-chat",
            datetime.now(timezone.utc),
        )


@pytest.mark.asyncio
async def test_mark_read_sunny(chat_service_with_bot: ChatService):
    await chat_service_with_bot.handle_incoming_message(
        "123456789",
        IncomingMessage(
            chat_id="100",
            message_id=1,
            text="u",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    )
    read_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    n = await chat_service_with_bot.mark_message_read("fixturebot", "100", read_at)
    assert n >= 1
