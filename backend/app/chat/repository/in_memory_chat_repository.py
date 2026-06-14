import asyncio

from ...models import Message, Status
from .chat_repository import ChatRepository


class InMemoryChatRepository(ChatRepository):
    """In-memory implementation of the chat DAL.

    Messages are organized per conversation (`chat_id`). All mutation goes
    through one asyncio.Lock so concurrent producers (REST handler, Telegram
    poller, webhook) never interleave a read/modify/write — and so the
    active-chat admission in `register_chat` is race-free.

    Swapping this for a DB-backed repository (SQLAlchemy/Postgres) means
    implementing the same `ChatRepository` interface; nothing else changes.
    """

    def __init__(self, max_active_chats: int = 1) -> None:
        self._max_active_chats = max_active_chats
        # chat_id -> (message_id -> Message). The inner dict preserves insertion
        # order and lets update_message_status find a message within its conversation
        # without a global index (mirrors a table partitioned by chat_id).
        self._conversations: dict[int, dict[str, Message]] = {}
        self._active: set[int] = set()
        self._lock = asyncio.Lock()

    async def register_chat(self, chat_id: int) -> bool:
        async with self._lock:
            if chat_id in self._active:
                return True
            if len(self._active) >= self._max_active_chats:
                return False
            self._active.add(chat_id)
            self._conversations.setdefault(chat_id, {})
            return True

    async def is_active_chat(self, chat_id: int) -> bool:
        async with self._lock:
            return chat_id in self._active

    async def active_chats(self) -> list[int]:
        async with self._lock:
            return sorted(self._active)

    async def add_message(self, chat_id: int, message: Message) -> Message | None:
        async with self._lock:
            if chat_id not in self._active:
                return None
            self._conversations.setdefault(chat_id, {})[message.id] = message
            return message

    async def update_message_status(
        self, chat_id: int, message_id: str, status: Status
    ) -> Message | None:
        async with self._lock:
            message = self._conversations.get(chat_id, {}).get(message_id)
            if message is not None:
                message.status = status
            return message

    async def get_conversation(self, chat_id: int) -> list[Message]:
        async with self._lock:
            # Ordered by timestamp; stable, so equal timestamps keep insertion
            # order. The client renders this order as-is and never re-sorts.
            return sorted(
                self._conversations.get(chat_id, {}).values(),
                key=lambda m: m.timestamp,
            )

    async def reset(self) -> None:
        async with self._lock:
            self._conversations.clear()
            self._active.clear()
