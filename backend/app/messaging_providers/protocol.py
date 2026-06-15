from abc import ABC, abstractmethod
from dataclasses import dataclass

from .types import IncomingMessage


@dataclass(frozen=True)
class ProviderBotProfile:
    """Bot identity from the messaging provider (e.g. Telegram getMe)."""

    bot_id: int
    name: str
    username: str


class MessageProvider(ABC):
    """Outbound delivery, incoming parsing, and provider-side credentials."""

    @abstractmethod
    async def fetch_bot_profile(self, bot_id: int) -> ProviderBotProfile | None:
        """Resolve and validate bot metadata for a configured bot_id."""

    @abstractmethod
    async def send_message(self, bot_id: int, chat_id: str, text: str) -> bool:
        """Deliver text to a remote participant in an existing conversation."""

    @abstractmethod
    def parse_incoming_message(self, raw: dict) -> IncomingMessage | None:
        """Parse a provider-specific webhook/update payload, or return None."""

    @abstractmethod
    async def close(self) -> None:
        """Release provider resources (HTTP clients, connections, etc.)."""
