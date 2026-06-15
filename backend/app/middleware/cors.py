from typing import Any

from fastapi.middleware.cors import CORSMiddleware

from ..bootstrap import AppContext


def register_cors(app_context: AppContext) -> tuple[type, dict[str, Any]]:
    return (
        CORSMiddleware,
        {
            "allow_origins": app_context.settings.cors_allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        },
    )
