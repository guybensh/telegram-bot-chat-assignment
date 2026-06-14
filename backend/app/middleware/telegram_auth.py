import logging
from urllib.parse import urlparse

from fastapi import Depends, Header, HTTPException, Request

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)


def expected_webhook_path(webhook_path: str, bot_token: str) -> str:
    return f"{webhook_path.rstrip('/')}/{bot_token}"


def _request_host(request: Request) -> str:
    forwarded_host = request.headers.get("X-Forwarded-Host")
    if forwarded_host:
        return forwarded_host.split(",")[0].strip().split(":")[0]
    return request.url.hostname or ""


def _matches_registered_webhook(request: Request, settings: Settings) -> bool:
    if request.url.path != expected_webhook_path(
        settings.telegram_webhook_path, settings.telegram_bot_token
    ):
        return False

    if not settings.telegram_webhook_url:
        return True

    expected_host = urlparse(settings.telegram_webhook_url).hostname
    if expected_host and _request_host(request) != expected_host:
        return False

    return True


async def telegram_authentication(
    request: Request,
    bot_token: str,
    settings: Settings = Depends(get_settings),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> None:
    """Route-scoped guard for the webhook — FastAPI's equivalent of
    ``app.use('/telegram/webhook', verify)`` in Express."""
    if not _matches_registered_webhook(request, settings):
        logger.warning("Blocked webhook request with unexpected URL: %s", request.url)
        raise HTTPException(status_code=403, detail="Forbidden")

    if bot_token != settings.telegram_bot_token:
        raise HTTPException(status_code=403, detail="Invalid bot token")

    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid secret token")
