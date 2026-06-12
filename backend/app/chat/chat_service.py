import logging
from datetime import datetime

from ..connection_manager import ConnectionManager
from ..models import Message, Sender, Status
from ..telegram_service import IncomingMessage, TelegramService
from .repository import ChatRepository

logger = logging.getLogger(__name__)


class NoActiveConversationError(Exception):
    """Raised when the agent tries to send to a chat that isn't active. A
    Telegram bot cannot initiate a conversation, so there is nowhere to deliver
    until the participant has messaged the bot first."""


class ChatService:
    """The chat domain — the single place that decides how messages are
    processed in each direction.

    It coordinates three collaborators that have no knowledge of one another:
    the chat repository (DAL — state), the connection manager (agent clients),
    and the Telegram gateway (delivery + receipt of updates). It depends on the
    `ChatRepository` interface, not a concrete store, so persistence is
    swappable. The active-conversation limit is injected from configuration.
    """

    def __init__(
        self,
        repository: ChatRepository,
        manager: ConnectionManager,
        telegram: TelegramService,
        max_active_chats: int = 1,
    ) -> None:
        self._repository = repository
        self._manager = manager
        self._telegram = telegram
        self._max_active_chats = max_active_chats

    async def list_conversations(self) -> list[int]:
        return await self._repository.active_chats()

    async def get_history(self, chat_id: int) -> list[Message]:
        return await self._repository.list(chat_id)

    async def reset(self) -> None:
        """Admin/dev: clear all conversation state and tell every connected
        client to reset, so the no-active-chat flow can be exercised again."""
        await self._repository.reset()
        await self._manager.broadcast({"type": "reset"})

    # --- outgoing: agent -> Telegram participant ------------------------

    async def send_message(
        self, message_id: str, chat_id: int, text: str, timestamp: datetime
    ) -> Message:
        """Store an outgoing message, deliver it to the participant, record the
        outcome, and broadcast a receipt so every agent client converges.

        Raises NoActiveConversationError if `chat_id` is not an active chat — the
        bot can only reply within a conversation the participant started."""
        if not await self._repository.is_active_chat(chat_id):
            raise NoActiveConversationError(chat_id)

        message = Message(
            id=message_id,
            chat_id=chat_id,
            text=text,
            timestamp=timestamp,
            sender=Sender.AGENT,
            status=Status.PENDING,
        )
        await self._repository.add(chat_id, message)

        delivered = await self._telegram.send(chat_id, text)
        status = Status.SENT if delivered else Status.FAILED

        await self._repository.update_status(chat_id, message.id, status)
        message.status = status
        logger.info("Outgoing [chat %s] %r -> %s", chat_id, text[:200], status.value)
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
        connected first, then admit the conversation (subject to the configured
        limit), store it, and push it to every connected client."""
        # The agent must connect first — reject if no client is present.
        if not self._manager.has_clients():
            logger.info(
                "No agent connected; rejecting incoming from chat %s",
                incoming.chat_id,
            )
            return

        if not await self._repository.register_chat(
            incoming.chat_id, self._max_active_chats
        ):
            logger.info(
                "At active-chat capacity (%d); ignoring chat %s",
                self._max_active_chats,
                incoming.chat_id,
            )
            return

        message = Message(
            id=f"tg-{incoming.message_id}",
            chat_id=incoming.chat_id,
            text=incoming.text,
            timestamp=incoming.timestamp,
            sender=Sender.USER,
            status=Status.RECEIVED,
        )
        await self._repository.add(incoming.chat_id, message)
        logger.info(
            "Incoming [chat %s] %r", incoming.chat_id, incoming.text[:200]
        )
        await self._manager.broadcast(
            {"type": "message", **message.model_dump(mode="json")}
        )
