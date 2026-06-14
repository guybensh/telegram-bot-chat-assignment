import logging

from fastapi import APIRouter, Depends, Request

from ..domain.bot import BotNotFoundError, BotService
from ..domain.chat import ChatService
from ..middleware import telegram_authentication
from ..messaging_providers.telegram import TelegramService

logger = logging.getLogger(__name__)


def build_webhook_router(
    *,
    parser: TelegramService,
    chat: ChatService,
    bot_service: BotService,
    webhook_path: str,
) -> APIRouter:
    """Webhook routes with guards attached only to this router (Express-style)."""
    router = APIRouter(
        prefix=webhook_path.rstrip("/"),
        tags=["telegram"],
        dependencies=[Depends(telegram_authentication)],
    )

    @router.post("/{bot_token}")
    async def telegram_webhook(request: Request, bot_token: str) -> dict[str, bool]:
        try:
            bot = await bot_service.get_record_by_token(bot_token)
        except BotNotFoundError:
            logger.warning("Webhook for unknown bot token")
            return {"ok": True}

        incoming = parser.process_update(await request.json())
        if incoming is not None:
            logger.info(
                "Update via WEBHOOK (bot=%s, chat=%s)",
                bot.username,
                incoming.chat_id,
            )
            await chat.handle_incoming(bot.bot_id, incoming)
        return {"ok": True}

    return router
