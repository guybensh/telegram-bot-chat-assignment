from contextlib import asynccontextmanager

from fastapi import FastAPI

from .bootstrap import build_app_context, load_bots_from_config
from .app_factory import create_app
from .listeners import create_listeners

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


app = create_app(app_context, lifespan=lifespan)
