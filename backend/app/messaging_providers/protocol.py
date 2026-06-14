from abc import ABC, abstractmethod
from dataclasses import dataclass

from .types import IncomingMessage


@dataclass(frozen=True)
class ProviderBotProfile:
    """Bot identity resolved from provider credentials (e.g. a bot token)."""

    bot_id: int
    name: str
    username: str


class MessageProvider(ABC):
    """Outbound delivery, bot registration, and incoming payload parsing."""

    @abstractmethod
    async def resolve_bot(self, credentials: str) -> ProviderBotProfile | None:
        """Resolve provider credentials into bot profile metadata."""

    @abstractmethod
    async def send_message(self, credentials: str, chat_id: int, text: str) -> bool:
        """Deliver text to a remote participant in an existing conversation."""

    @abstractmethod
    def parse_incoming_message(self, raw: dict) -> IncomingMessage | None:
        """Parse a provider-specific webhook/update payload, or return None."""

    @abstractmethod
    async def close(self) -> None:
        """Release provider resources (HTTP clients, connections, etc.)."""
