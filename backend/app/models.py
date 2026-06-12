from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Sender(str, Enum):
    """Who sent the message, from the app's perspective."""

    USER = "user"  # sent from our frontend (delivered to Telegram via the bot)
    BOT = "bot"    # received from the remote Telegram participant


class Status(str, Enum):
    # Outgoing lifecycle:
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    # Incoming (constant):
    RECEIVED = "received"


class Message(BaseModel):
    """The single message shape shared by REST responses and WebSocket events,
    matching the frontend's model exactly."""

    id: str
    text: str
    timestamp: datetime
    sender: Sender
    status: Status


class SendMessageRequest(BaseModel):
    """Body of POST /messages. The client sends the full message object, but the
    server only trusts these fields — `sender` and `status` are assigned
    server-side so a client can never post as the bot or fake a delivery state.
    Unknown fields are ignored."""

    id: str
    text: str
    timestamp: datetime
