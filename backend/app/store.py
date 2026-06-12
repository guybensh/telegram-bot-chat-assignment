import asyncio

from .chat_repository import ChatRepository
from .models import Message, Status


class InMemoryChatRepository(ChatRepository):
    """In-memory implementation of the chat DAL.

    Messages are organized per conversation (`chat_id`). All mutation goes
    through one asyncio.Lock so concurrent producers (REST handler, Telegram
    poller, webhook) never interleave a read/modify/write — and so the
    active-chat admission in `register_chat` is race-free.

    Swapping this for a DB-backed repository (SQLAlchemy/Postgres) means
    implementing the same `ChatRepository` interface; nothing else changes.
    """

    def __init__(self) -> None:
        self._conversations: dict[int, list[Message]] = {}
        self._by_id: dict[str, Message] = {}
        self._active: set[int] = set()
        self._lock = asyncio.Lock()

    async def register_chat(self, chat_id: int, max_active: int) -> bool:
        async with self._lock:
            if chat_id in self._active:
                return True
            if len(self._active) >= max_active:
                return False
            self._active.add(chat_id)
            self._conversations.setdefault(chat_id, [])
            return True

    async def is_active_chat(self, chat_id: int) -> bool:
        async with self._lock:
            return chat_id in self._active

    async def active_chats(self) -> list[int]:
        async with self._lock:
            return sorted(self._active)

    async def add(self, message: Message) -> Message:
        async with self._lock:
            self._conversations.setdefault(message.chat_id, []).append(message)
            self._by_id[message.id] = message
            return message

    async def update_status(self, message_id: str, status: Status) -> Message | None:
        async with self._lock:
            message = self._by_id.get(message_id)
            if message is not None:
                message.status = status
            return message

    async def list(self, chat_id: int) -> list[Message]:
        async with self._lock:
            # Ordered by timestamp; stable, so equal timestamps keep insertion
            # order. The client renders this order as-is and never re-sorts.
            return sorted(
                self._conversations.get(chat_id, []), key=lambda m: m.timestamp
            )

    async def reset(self) -> None:
        async with self._lock:
            self._conversations.clear()
            self._by_id.clear()
            self._active.clear()
