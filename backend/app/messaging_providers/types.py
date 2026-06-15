from dataclasses import dataclass
from datetime import datetime


@dataclass
class IncomingMessage:
    """Provider-neutral incoming text message from a remote participant."""

    chat_id: int
    message_id: int
    text: str
    timestamp: datetime
