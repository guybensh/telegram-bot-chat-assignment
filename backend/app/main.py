from contextlib import asynccontextmanager

from fastapi import FastAPI

from .bootstrap import build_app_context, load_bots_from_config
from .listeners import create_listeners
from .middleware import register_cors
from .routes import app_router, webhook_router

app_context = build_app_context()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bots = await load_bots_from_config(app_context)
    listeners = create_listeners(app_context)
    for listener in listeners:
        await listener.start(app_context, bots)
    try:
        yield
    finally:
        for listener in listeners:
            await listener.stop()


app = FastAPI(title="Telegram Chat Backend", lifespan=lifespan)

cors_middleware, cors_options = register_cors(app_context)
app.add_middleware(cors_middleware, **cors_options)

app.include_router(app_router(app_context))
app.include_router(webhook_router(app_context))
