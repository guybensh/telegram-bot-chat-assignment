"""Shared helpers for backend tests."""

from datetime import datetime, timezone

from app.domain.chat import ChatService
from app.messaging_providers import IncomingMessage


async def admit_user_message(
    chat_service: ChatService,
    *,
    chat_id: str = "999888777",
    message_id: int = 1,
    text: str = "hi from telegram user",
) -> None:
    """Simulate an incoming user message so `chat_id` becomes an active thread."""
    await chat_service.handle_incoming_message(
        "123456789",
        IncomingMessage(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            timestamp=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ),
    )
