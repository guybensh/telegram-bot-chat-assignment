import logging

from fastapi import APIRouter, Depends, Request

from ..bootstrap import AppContext
from ..domain.bot import BotNotFoundError
from ..middleware import build_telegram_authentication

logger = logging.getLogger(__name__)


def webhook_router(app_context: AppContext) -> APIRouter:
    """Webhook routes with guards attached only to this router (Express-style)."""
    router = APIRouter(
        prefix=app_context.settings.telegram_webhook_path.rstrip("/"),
        tags=["telegram"],
        dependencies=[Depends(build_telegram_authentication(app_context))],
    )

    @router.post("/{bot_id}")
    async def telegram_webhook(request: Request, bot_id: int) -> dict[str, bool]:
        try:
            bot = await app_context.bot_service.get_by_id(bot_id)
        except BotNotFoundError:
            logger.warning(
                "[Webhook::telegram_webhook]: Webhook for unknown bot_id=%s", bot_id
            )
            return {"ok": True}

        incoming = app_context.message_provider.parse_incoming_message(
            await request.json()
        )
        if incoming is not None:
            logger.info(
                "[Webhook::telegram_webhook]: Update via WEBHOOK (bot=%s, chat=%s)",
                bot.username,
                incoming.chat_id,
            )
            await app_context.chat_service.handle_incoming(bot.bot_id, incoming)
        return {"ok": True}

    return router
