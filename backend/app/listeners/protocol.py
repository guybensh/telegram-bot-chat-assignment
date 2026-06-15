from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..bootstrap import AppContext
    from ..domain.bot.record import BotRecord


class MessageListener(ABC):
    """Attaches the incoming message path for a deployment mode (webhook, poll, etc.)."""

    @abstractmethod
    async def start(self, app_context: "AppContext", bots: list["BotRecord"]) -> None:
        """Wire up incoming delivery for the registered bots."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop background tasks and release listener resources."""
