import logging
from collections.abc import Callable, Coroutine
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, Header, HTTPException, Request

from ..bootstrap import AppContext
from ..config import Settings, get_settings
from ..domain.bot import BotNotFoundError

logger = logging.getLogger(__name__)


def expected_webhook_path(webhook_path: str, bot_id: int) -> str:
    return f"{webhook_path.rstrip('/')}/{bot_id}"


def _request_host(request: Request) -> str:
    forwarded_host = request.headers.get("X-Forwarded-Host")
    if forwarded_host:
        return forwarded_host.split(",")[0].strip().split(":")[0]
    return request.url.hostname or ""


def _matches_webhook_host(request: Request, settings: Settings) -> bool:
    if not settings.telegram_webhook_url:
        return True

    expected_host = urlparse(settings.telegram_webhook_url).hostname
    if expected_host and _request_host(request) != expected_host:
        return False
    return True


def build_telegram_authentication(
    app_context: AppContext,
) -> Callable[..., Coroutine[Any, Any, None]]:
    """Route-scoped guard factory for the webhook router."""

    async def telegram_authentication(
        request: Request,
        bot_id: int,
        settings: Settings = Depends(get_settings),
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> None:
        if request.url.path != expected_webhook_path(
            settings.telegram_webhook_path, bot_id
        ):
            logger.warning(
                "[TelegramAuth::telegram_authentication]: Blocked webhook request with unexpected URL: %s",
                request.url,
            )
            raise HTTPException(status_code=403, detail="Forbidden")

        if not _matches_webhook_host(request, settings):
            logger.warning(
                "[TelegramAuth::telegram_authentication]: Blocked webhook request with unexpected host: %s",
                request.url,
            )
            raise HTTPException(status_code=403, detail="Forbidden")

        try:
            await app_context.bot_service.get_by_id(bot_id)
        except BotNotFoundError:
            raise HTTPException(status_code=403, detail="Invalid bot")

        if settings.telegram_webhook_secret:
            if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
                raise HTTPException(status_code=403, detail="Invalid secret token")

    return telegram_authentication
