import logging
from datetime import datetime

from .connection_manager import ConnectionManager
from .models import Message, Sender, Status
from .store import ChatStore
from .telegram_service import IncomingMessage, TelegramService

logger = logging.getLogger(__name__)


class ChatService:
    """The chat domain — the single place that decides how messages are
    processed in each direction.

    It coordinates three collaborators that have no knowledge of one another:
    the message store (state), the connection manager (WebSocket clients), and
    the Telegram gateway (delivery + receipt of updates). Swapping any one of
    them out leaves this orchestration unchanged.
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

    async def get_history(self) -> list[Message]:
        return await self._store.list()

    # --- outgoing: user -> Telegram -------------------------------------

    async def send_user_message(
        self, message_id: str, text: str, timestamp: datetime
    ) -> Message:
        """Store an outgoing user message, deliver it to the active chat, record
        the outcome, and broadcast a receipt so every connected client
        converges. The server owns sender/status — the client cannot set them."""
        message = Message(
            id=message_id,
            text=text,
            timestamp=timestamp,
            sender=Sender.USER,
            status=Status.PENDING,
        )
        await self._store.add(message)

        chat_id = await self._store.get_chat_id()
        delivered = await self._telegram.send(chat_id, text)
        status = Status.SENT if delivered else Status.FAILED

        await self._store.update_status(message.id, status)
        message.status = status
        await self._manager.broadcast(
            {"type": "receipt", "message_id": message.id, "status": status.value}
        )
        return message

    # --- incoming: Telegram -> clients ----------------------------------

    async def handle_incoming(self, incoming: IncomingMessage) -> None:
        """Process a message received from Telegram: enforce the single-active-
        chat policy, store it, then push it to every connected client."""
        if not await self._store.bind_chat(incoming.chat_id):
            logger.info("Ignoring message from non-active chat %s", incoming.chat_id)
            return

        message = Message(
            id=f"tg-{incoming.message_id}",
            text=incoming.text,
            timestamp=incoming.timestamp,
            sender=Sender.BOT,
            status=Status.RECEIVED,
        )
        await self._store.add(message)
        await self._manager.broadcast(
            {"type": "message", **message.model_dump(mode="json")}
        )
