import logging

from fastapi import APIRouter, Depends, Request

from ..chat import ChatService
from ..middleware import telegram_authentication
from ..messaging_providers.telegram import TelegramService

logger = logging.getLogger(__name__)


def build_webhook_router(
    *,
    telegram: TelegramService,
    chat: ChatService,
    webhook_path: str,
) -> APIRouter:
    """Webhook routes with guards attached only to this router (Express-style)."""
    router = APIRouter(
        prefix=webhook_path.rstrip("/"),
        tags=["telegram"],
        dependencies=[Depends(telegram_authentication)],
    )

    @router.post("/{bot_token}")
    async def telegram_webhook(request: Request) -> dict[str, bool]:
        incoming = telegram.process_update(await request.json())
        if incoming is not None:
            logger.info("Update via WEBHOOK (chat=%s)", incoming.chat_id)
            await chat.handle_incoming(incoming)
        return {"ok": True}

    return router
