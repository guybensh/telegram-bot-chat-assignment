import logging
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from .chat import ChatService, NoActiveConversationError
from .chat.repository import InMemoryChatRepository
from .config import get_settings
from .connection_manager import ConnectionManager
from .models import Message, SendMessageRequest
from .messaging_providers.telegram import TelegramAPI, TelegramService
from .messaging_providers.telegram.poller import TelegramPoller
from .messaging_providers.telegram.utils import generate_telegram_webhook_url
from .routes import build_webhook_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class _RedactTokenFilter(logging.Filter):
    """Redacts the bot token from log records. httpx logs each request URL at
    INFO (which includes the token); we keep those logs — they show the live
    getUpdates/sendMessage responses — but never leak the token."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if self._token in message:
            record.msg = message.replace(self._token, "<token>")
            record.args = ()
        return True


# Surface httpx's request/response lines (the Telegram polling responses), with
# the token redacted so it never lands in logs.
if settings.telegram_bot_token:
    logging.getLogger("httpx").addFilter(
        _RedactTokenFilter(settings.telegram_bot_token)
    )
chat_repository = InMemoryChatRepository(max_active_chats=settings.max_active_chats)
connection_manager = ConnectionManager()
telegram_api = TelegramAPI(settings.telegram_bot_token, settings.telegram_api_base)
telegram = TelegramService(telegram_api, mock=settings.telegram_mode == "mock")
chat = ChatService(chat_repository, connection_manager, telegram)
# Drives the pull mechanism: fetches/parses updates in a loop and passes each
# to chat.handle_incoming. (Webhook mode delivers inline in the webhook route.)
poller = TelegramPoller(telegram, chat)


async def _start_mock_mode() -> None:
    logger.info("Mock mode: simulated delivery + a fake incoming message every 10s")
    await poller.start_mock_feed()


async def _start_webhook_mode() -> None:
    url = generate_telegram_webhook_url(
        public_base_url=settings.telegram_webhook_url,
        webhook_path=settings.telegram_webhook_path,
        bot_token=settings.telegram_bot_token,
    )
    ok = await telegram_api.set_webhook(
        url, settings.telegram_webhook_secret or None
    )
    safe_url = url.replace(settings.telegram_bot_token, "<token>")
    logger.info("Webhook mode: setWebhook(%s) -> ok=%s", safe_url, ok)


async def _start_polling_mode() -> None:
    # Polling needs no public URL; clear any stale webhook so Telegram delivers
    # via getUpdates.
    await telegram_api.delete_webhook()
    await poller.start_polling()
    logger.info("Polling mode: started")


async def _start_telegram_receive() -> None:
    if settings.telegram_mode == "mock":
        await _start_mock_mode()
        return

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram integration disabled")
        return

    if settings.telegram_mode == "webhook":
        await _start_webhook_mode()
    else:
        await _start_polling_mode()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the chosen Telegram receive strategy on boot, tear it down on exit."""
    await _start_telegram_receive()
    try:
        yield
    finally:
        await poller.stop()
        await telegram_api.close()


app = FastAPI(title="Telegram Chat Backend", lifespan=lifespan)

# CORS for the browser-facing API only (frontend origin). Webhook traffic is
# server-to-server and does not use CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(
    build_webhook_router(
        telegram=telegram,
        chat=chat,
        webhook_path=settings.telegram_webhook_path,
    )
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/admin/reset")
async def admin_reset():
    """Dev/admin: clear all conversations so the 'no active chat' flow can be
    re-tested without restarting the server."""
    await chat.reset()
    return {"status": "reset"}


@app.get("/conversations")
async def get_conversations():
    """List the active conversations (chat_ids) so the client knows what exists
    and which chat to reply to."""
    return [{"chat_id": chat_id} for chat_id in await chat.list_conversations()]


@app.get("/messages", response_model=list[Message])
async def get_messages(chat_id: int):
    """Return one conversation's message history, ordered by timestamp."""
    return await chat.get_history(chat_id)


@app.post("/messages", response_model=Message)
async def post_message(payload: SendMessageRequest):
    """Forward an outgoing message to the given conversation. The chat service
    owns the processing; the route only translates HTTP <-> domain."""
    try:
        return await chat.send_message(
            payload.id, payload.chat_id, payload.text, payload.timestamp
        )
    except NoActiveConversationError:
        raise HTTPException(
            status_code=409,
            detail="No active conversation for this chat_id — the participant must message the bot first",
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Server-push channel: incoming messages and delivery receipts. The client
    never sends over this socket, so the receive loop exists only to keep the
    connection open and detect disconnects."""
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
