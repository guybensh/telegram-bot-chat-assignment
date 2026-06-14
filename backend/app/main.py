import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .domain.bot.bootstrap import load_bots_from_config
from .deps import build_dependencies
from .routes import build_webhook_router
from .routes.api import register_routes

logger = logging.getLogger(__name__)
deps = build_dependencies()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bots = await load_bots_from_config(
        deps.settings, deps.bot_service, deps.telegram_gateway
    )
    for bot in bots:
        logger.info("Registered bot @%s (bot_id=%s)", bot.username, bot.bot_id)
    await deps.telegram_runtime.start(bots)
    try:
        yield
    finally:
        await deps.telegram_runtime.stop()


app = FastAPI(title="Telegram Chat Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=deps.settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(register_routes(deps))
app.include_router(
    build_webhook_router(
        parser=deps.telegram_parser,
        chat=deps.chat,
        bot_service=deps.bot_service,
        webhook_path=deps.settings.telegram_webhook_path,
    )
)
