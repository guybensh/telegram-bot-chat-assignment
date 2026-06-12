import asyncio

from .models import Message, Status


class ChatStore:
    """In-memory message store plus single-active-chat session state.

    This is the swappable persistence layer from the architecture plan: every
    method is async and the interface is intentionally small, so a DB-backed
    implementation (SQLAlchemy/Postgres) can drop in with no caller changes.

    All mutation goes through one asyncio.Lock so concurrent producers — the
    REST handler, the Telegram poller, and the webhook route — never interleave
    a read/modify/write on the shared state.
    """

    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._by_id: dict[str, Message] = {}
        self._chat_id: int | None = None
        self._lock = asyncio.Lock()

    async def add(self, message: Message) -> Message:
        async with self._lock:
            self._messages.append(message)
            self._by_id[message.id] = message
            return message

    async def update_status(self, message_id: str, status: Status) -> Message | None:
        async with self._lock:
            message = self._by_id.get(message_id)
            if message is not None:
                message.status = status
            return message

    async def list(self) -> list[Message]:
        async with self._lock:
            # Ordered by timestamp; stable, so equal timestamps keep insertion
            # order. The client renders this order as-is and never re-sorts.
            return sorted(self._messages, key=lambda m: m.timestamp)

    # --- single-active-chat session state --------------------------------

    async def bind_chat(self, chat_id: int) -> bool:
        """Bind to `chat_id` if no chat is active yet. Returns True if this chat
        is the active one (just bound, or already matching), False if a
        different chat is already bound and this one must be ignored."""
        async with self._lock:
            if self._chat_id is None:
                self._chat_id = chat_id
                return True
            return self._chat_id == chat_id

    async def get_chat_id(self) -> int | None:
        async with self._lock:
            return self._chat_id
