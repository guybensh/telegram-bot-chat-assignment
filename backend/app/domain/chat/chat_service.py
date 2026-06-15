import logging
from datetime import datetime, timezone

from ..bot import BotNotFoundError, BotService
from ...connection_manager import ConnectionManager
from ...models import ChatSummary, Message, Sender, Status
from ...messaging_providers import IncomingMessage, MessageProvider
from .repository import ChatRepository

logger = logging.getLogger(__name__)


class NoActiveConversationError(Exception):
    """Raised when the agent tries to send to a chat that isn't active. A
    Telegram bot cannot initiate a conversation, so there is nowhere to deliver
    until the participant has messaged the bot first."""


class ChatService:
    """The chat domain — message processing scoped per bot."""

    def __init__(
        self,
        repository: ChatRepository,
        connection_manager: ConnectionManager,
        messaging: MessageProvider,
        bot_service: BotService,
    ) -> None:
        self._repository = repository
        self._connection_manager = connection_manager
        self._messaging_provider = messaging
        self._bot_service = bot_service

    async def list_chat_summaries(
        self, username: str
    ) -> list[ChatSummary]:
        bot = await self._bot_service.get_by_username(username)
        summaries: list[ChatSummary] = []
        for chat_id in await self._repository.list_active_chats(bot.bot_id):
            messages = await self._repository.get_conversation(bot.bot_id, chat_id)
            last = messages[-1] if messages else None
            summaries.append(
                ChatSummary(
                    chat_id=chat_id,
                    bot_id=bot.bot_id,
                    bot_username=bot.username,
                    title=f"Chat {chat_id}",
                    last_message_text=last.text if last else None,
                    last_message_at=last.timestamp if last else None,
                    last_sender=last.sender if last else None,
                )
            )
        return sorted(
            summaries,
            key=lambda item: item.last_message_at
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    async def count_active_chats(self, bot_id: str) -> int:
        return len(await self._repository.list_active_chats(bot_id))

    async def list_messages(self, username: str, chat_id: str) -> list[Message]:
        bot = await self._bot_service.get_by_username(username)
        return await self._repository.get_conversation(bot.bot_id, chat_id)

    async def mark_message_read(
        self, username: str, chat_id: str, read_at: datetime
    ) -> int:
        bot = await self._bot_service.get_by_username(username)
        if not await self._repository.is_active_chat(bot.bot_id, chat_id):
            raise NoActiveConversationError(chat_id)
        return await self._repository.mark_message_read(
            bot.bot_id, chat_id, read_at
        )

    async def send_message(
        self,
        username: str,
        message_id: str,
        chat_id: str,
        text: str,
        timestamp: datetime,
    ) -> Message:
        bot = await self._bot_service.get_by_username(username)
        message = Message(
            id=message_id,
            bot_id=bot.bot_id,
            chat_id=chat_id,
            text=text,
            timestamp=timestamp,
            sender=Sender.AGENT,
            status=Status.PENDING,
        )
        stored = await self._repository.add_message(bot.bot_id, chat_id, message)
        if stored is None:
            raise NoActiveConversationError(chat_id)

        delivered = await self._messaging_provider.send_message(bot.bot_id, chat_id, text)
        status = Status.SENT if delivered else Status.FAILED

        await self._repository.update_message_status(
            bot.bot_id, chat_id, message.id, status
        )
        message.status = status
        logger.info(
            "[send_message]: Outgoing [bot %s chat %s] %r -> %s",
            bot.username,
            chat_id,
            text[:200],
            status.value,
        )
        await self._connection_manager.broadcast(
            {
                "type": "receipt",
                "bot_id": bot.bot_id,
                "bot_username": bot.username,
                "message_id": message.id,
                "chat_id": chat_id,
                "status": status.value,
            }
        )
        return message

    async def handle_incoming_message(
        self, bot_id: str, incoming: IncomingMessage
    ) -> None:
        try:
            bot = await self._bot_service.get_by_id(bot_id)
        except BotNotFoundError:
            logger.warning(
                "[handle_incoming_message]: Incoming for unknown bot_id %s; ignoring",
                bot_id,
            )
            return

        message = Message(
            id=f"tg-{incoming.message_id}",
            bot_id=bot.bot_id,
            chat_id=incoming.chat_id,
            text=incoming.text,
            timestamp=incoming.timestamp,
            sender=Sender.USER,
            status=Status.RECEIVED,
        )
        if not await self._repository.create(
            bot.bot_id, incoming.chat_id, bot.max_chats
        ):
            logger.info(
                "[handle_incoming_message]: At active-chat capacity for bot %s; ignoring chat %s",
                bot.username,
                incoming.chat_id,
            )
            return

        stored = await self._repository.add_message(
            bot.bot_id, incoming.chat_id, message
        )
        if stored is None:
            return

        logger.info(
            "[handle_incoming_message]: Incoming [bot %s chat %s] %r",
            bot.username,
            incoming.chat_id,
            incoming.text[:200],
        )

        if not await self._connection_manager.has_clients():
            logger.info(
                "[handle_incoming_message]: Stored incoming from chat %s; no agent connected to broadcast",
                incoming.chat_id,
            )
            return

        await self._connection_manager.broadcast(
            {
                "type": "message",
                "bot_username": bot.username,
                **message.model_dump(mode="json"),
            }
        )

    async def reset(self) -> None:
        await self._repository.delete()
        await self._connection_manager.broadcast({"type": "reset"})
