from abc import ABC, abstractmethod

from ...models import Message, Status


class ChatRepository(ABC):
    """Data-access layer (DAL) for conversations and their messages.

    `ChatService` depends on this abstraction rather than a concrete store, so
    the storage backend can be swapped — in-memory today, a database tomorrow —
    without changing any domain logic. The current implementation is
    `InMemoryChatRepository`; a DB-backed one would implement the same interface.

    Concurrency contract: `register_chat` must perform its capacity check and
    admission atomically with respect to concurrent callers, so the active-chat
    limit can never be exceeded by a race.
    """

    @abstractmethod
    async def register_chat(self, chat_id: int, max_active: int) -> bool:
        """Admit `chat_id` as an active conversation if it is already active, or
        if there is capacity (fewer than `max_active` active chats). Returns
        whether the chat is active afterward."""

    @abstractmethod
    async def is_active_chat(self, chat_id: int) -> bool:
        """Whether `chat_id` is an active conversation."""

    @abstractmethod
    async def active_chats(self) -> list[int]:
        """The chat_ids of all active conversations."""

    @abstractmethod
    async def add(self, chat_id: int, message: Message) -> Message:
        """Persist `message` in conversation `chat_id`."""

    @abstractmethod
    async def update_status(
        self, chat_id: int, message_id: str, status: Status
    ) -> Message | None:
        """Update the status of message `message_id` within conversation
        `chat_id`; returns the message, or None if not found."""

    @abstractmethod
    async def list(self, chat_id: int) -> list[Message]:
        """A conversation's messages, ordered by timestamp."""

    @abstractmethod
    async def reset(self) -> None:
        """Clear all conversations, messages, and active-chat state."""
