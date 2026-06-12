import asyncio

from .models import Message, Status

# The assignment accepts a single active conversation. This is a *policy*, not a
# structural limit: storage and routing are already per-chat_id, so allowing
# many conversations is just flipping this off (and dropping the check below).
_SINGLE_ACTIVE_CHAT = True


class ChatStore:
    """In-memory message store, organized per conversation (`chat_id`).

    This is the swappable persistence layer from the architecture plan: every
    method is async and the interface is small, so a DB-backed implementation
    drops in with no caller changes. All mutation goes through one asyncio.Lock
    so concurrent producers (REST handler, Telegram poller, webhook) never
    interleave a read/modify/write.
    """

    def __init__(self) -> None:
        self._conversations: dict[int, list[Message]] = {}
        self._by_id: dict[str, Message] = {}
        self._active: set[int] = set()
        self._lock = asyncio.Lock()

    # --- conversation policy --------------------------------------------

    async def register_chat(self, chat_id: int) -> bool:
        """Admit a conversation under the single-active-chat policy. Returns
        True if `chat_id` is active (already known, or newly admitted), False if
        a different chat is already active and this one must be ignored."""
        async with self._lock:
            if chat_id in self._active:
                return True
            if _SINGLE_ACTIVE_CHAT and self._active:
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

    # --- messages --------------------------------------------------------

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
        """Clear all conversations, messages, and active-chat state. A dev/admin
        affordance for re-testing the no-conversation flow without a restart."""
        async with self._lock:
            self._conversations.clear()
            self._by_id.clear()
            self._active.clear()
