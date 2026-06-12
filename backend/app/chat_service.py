import logging
from datetime import datetime

from .connection_manager import ConnectionManager
from .models import Message, Sender, Status
from .store import ChatStore
from .telegram_service import IncomingMessage, TelegramService

logger = logging.getLogger(__name__)


class NoActiveConversationError(Exception):
    """Raised when the agent tries to send to a chat that isn't active. A
    Telegram bot cannot initiate a conversation, so there is nowhere to deliver
    until the participant has messaged the bot first."""


class ChatService:
    """The chat domain — the single place that decides how messages are
    processed in each direction.

    It coordinates three collaborators that have no knowledge of one another:
    the message store (state), the connection manager (agent clients), and
    the Telegram gateway (delivery + receipt of updates).
    """

    def __init__(
        self,
        store: ChatStore,
        manager: ConnectionManager,
        telegram: TelegramService,
    ) -> None:
        self._store = store
        self._manager = manager
        self._telegram = telegram

    async def list_conversations(self) -> list[int]:
        return await self._store.active_chats()

    async def get_history(self, chat_id: int) -> list[Message]:
        return await self._store.list(chat_id)

    async def reset(self) -> None:
        """Admin/dev: clear all conversation state and tell every connected
        client to reset, so the no-active-chat flow can be exercised again."""
        await self._store.reset()
        await self._manager.broadcast({"type": "reset"})

    # --- outgoing: agent -> Telegram participant ------------------------

    async def send_message(
        self, message_id: str, chat_id: int, text: str, timestamp: datetime
    ) -> Message:
        """Store an outgoing message, deliver it to the participant, record the
        outcome, and broadcast a receipt so every agent client converges.

        Raises NoActiveConversationError if `chat_id` is not an active chat — the
        bot can only reply within a conversation the participant started."""
        if not await self._store.is_active_chat(chat_id):
            raise NoActiveConversationError(chat_id)

        message = Message(
            id=message_id,
            chat_id=chat_id,
            text=text,
            timestamp=timestamp,
            sender=Sender.AGENT,
            status=Status.PENDING,
        )
        await self._store.add(message)

        delivered = await self._telegram.send(chat_id, text)
        status = Status.SENT if delivered else Status.FAILED

        await self._store.update_status(message.id, status)
        message.status = status
        await self._manager.broadcast(
            {
                "type": "receipt",
                "message_id": message.id,
                "chat_id": chat_id,
                "status": status.value,
            }
        )
        return message

    # --- incoming: Telegram participant -> agent clients ----------------

    async def handle_incoming(self, incoming: IncomingMessage) -> None:
        """Process a message from a Telegram participant: an agent must be
        connected first, then enforce single-active-chat, store it, and push it
        to every connected client."""
        # The agent must connect first — reject if no client is present.
        if not self._manager.has_clients():
            logger.info(
                "No agent connected; rejecting incoming from chat %s",
                incoming.chat_id,
            )
            return

        if not await self._store.register_chat(incoming.chat_id):
            logger.info("Ignoring message from non-active chat %s", incoming.chat_id)
            return

        message = Message(
            id=f"tg-{incoming.message_id}",
            chat_id=incoming.chat_id,
            text=incoming.text,
            timestamp=incoming.timestamp,
            sender=Sender.USER,
            status=Status.RECEIVED,
        )
        await self._store.add(message)
        await self._manager.broadcast(
            {"type": "message", **message.model_dump(mode="json")}
        )
