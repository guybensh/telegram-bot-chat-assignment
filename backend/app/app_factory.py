"""Build the FastAPI application from an `AppContext` (used by `main` and tests)."""

from typing import Any, Callable

from fastapi import FastAPI

from .bootstrap import AppContext
from .middleware import register_cors
from .routes import app_router, webhook_router


def create_app(
    app_context: AppContext,
    *,
    lifespan: Callable[[FastAPI], Any] | None = None,
) -> FastAPI:
    """Compose routers and middleware. Pass `lifespan` for startup/shutdown hooks."""
    app = FastAPI(title="Telegram Chat Backend", lifespan=lifespan)
    cors_middleware, cors_options = register_cors(app_context)
    app.add_middleware(cors_middleware, **cors_options)
    app.include_router(app_router(app_context))
    app.include_router(webhook_router(app_context))
    return app
