import asyncio

from ....models import Message, Status
from .chat_repository import ChatRepository


class InMemoryChatRepository(ChatRepository):
    """In-memory implementation of the chat DAL, partitioned by bot_id."""

    def __init__(self) -> None:
        # bot_id -> chat_id -> (message_id -> Message)
        self._conversations: dict[int, dict[str, dict[str, Message]]] = {}
        self._active: dict[int, set[str]] = {}
        self._lock = asyncio.Lock()

    async def register_chat(
        self, bot_id: int, chat_id: str, max_chats: int
    ) -> bool:
        async with self._lock:
            active = self._active.setdefault(bot_id, set())
            if chat_id in active:
                return True
            if len(active) >= max_chats:
                return False
            active.add(chat_id)
            self._conversations.setdefault(bot_id, {}).setdefault(chat_id, {})
            return True

    async def is_active_chat(self, bot_id: int, chat_id: str) -> bool:
        async with self._lock:
            return chat_id in self._active.get(bot_id, set())

    async def active_chats(self, bot_id: int) -> list[str]:
        async with self._lock:
            return sorted(self._active.get(bot_id, set()))

    async def add_message(
        self, bot_id: int, chat_id: str, message: Message
    ) -> Message | None:
        async with self._lock:
            if chat_id not in self._active.get(bot_id, set()):
                return None
            self._conversations.setdefault(bot_id, {}).setdefault(chat_id, {})[
                message.id
            ] = message
            return message

    async def update_message_status(
        self, bot_id: int, chat_id: str, message_id: str, status: Status
    ) -> Message | None:
        async with self._lock:
            message = (
                self._conversations.get(bot_id, {}).get(chat_id, {}).get(message_id)
            )
            if message is None:
                return None
            message.status = status
            return message

    async def get_conversation(self, bot_id: int, chat_id: str) -> list[Message]:
        async with self._lock:
            messages = list(
                self._conversations.get(bot_id, {}).get(chat_id, {}).values(),
            )
            return sorted(messages, key=lambda message: message.timestamp)

    async def reset(self) -> None:
        async with self._lock:
            self._conversations.clear()
            self._active.clear()
