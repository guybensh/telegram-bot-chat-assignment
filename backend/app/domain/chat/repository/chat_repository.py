from abc import ABC, abstractmethod

from ....models import Message, Status


class ChatRepository(ABC):
    """Data-access layer (DAL) for conversations and their messages.

    All state is scoped by `bot_id` so multiple bots can share this store
    without chat_id collisions.
    """

    @abstractmethod
    async def register_chat(
        self, bot_id: int, chat_id: str, max_chats: int
    ) -> bool:
        """Admit `chat_id` for `bot_id` if already active or under that bot's
        capacity. Returns whether the chat is active afterward."""

    @abstractmethod
    async def is_active_chat(self, bot_id: int, chat_id: str) -> bool:
        """Whether `chat_id` is an active conversation for `bot_id`."""

    @abstractmethod
    async def active_chats(self, bot_id: int) -> list[str]:
        """Active chat_ids for one bot."""

    @abstractmethod
    async def add_message(
        self, bot_id: int, chat_id: str, message: Message
    ) -> Message | None:
        """Persist `message` when the chat is active; otherwise return None."""

    @abstractmethod
    async def update_message_status(
        self, bot_id: int, chat_id: str, message_id: str, status: Status
    ) -> Message | None:
        """Update delivery status for a message within a conversation."""

    @abstractmethod
    async def get_conversation(self, bot_id: int, chat_id: str) -> list[Message]:
        """A conversation's messages, ordered by timestamp."""

    @abstractmethod
    async def reset(self) -> None:
        """Clear all conversations, messages, and active-chat state."""
