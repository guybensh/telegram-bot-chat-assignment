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

    @router.post("/{bot_token}")
    async def telegram_webhook(request: Request, bot_token: str) -> dict[str, bool]:
        try:
            bot = await app_context.bot_service.get_record_by_token(bot_token)
        except BotNotFoundError:
            logger.warning("Webhook for unknown bot token")
            return {"ok": True}

        incoming = app_context.message_provider.parse_incoming_message(await request.json())
        if incoming is not None:
            logger.info(
                "Update via WEBHOOK (bot=%s, chat=%s)",
                bot.username,
                incoming.chat_id,
            )
            await app_context.chat_service.handle_incoming(bot.bot_id, incoming)
        return {"ok": True}

    return router
