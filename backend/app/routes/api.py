from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ..domain.bot import BotNotFoundError
from ..domain.bot.record import BotInboxItem
from ..domain.chat import NoActiveConversationError
from ..bootstrap import AppContext
from ..models import (
    ChatSummary,
    MarkThreadReadRequest,
    MarkThreadReadResponse,
    Message,
    SendMessageRequest,
)

router = APIRouter()


def app_router(deps: AppContext) -> APIRouter:
    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.post("/reset")
    async def admin_reset():
        await deps.chat_service.reset()
        return {"status": "reset"}

    @router.get("/bots", response_model=list[BotInboxItem])
    async def get_bots():
        records = await deps.bot_service.list_bots()
        items: list[BotInboxItem] = []
        for bot in records:
            active_chats = await deps.chat_service.count_active_chats(bot.bot_id)
            items.append(
                BotInboxItem(
                    bot_id=bot.bot_id,
                    bot_name=bot.bot_name,
                    username=bot.username,
                    max_chats=bot.max_chats,
                    active_chats=active_chats,
                )
            )
        return items

    @router.get(
        "/bots/{username}/chat-summaries",
        response_model=list[ChatSummary],
    )
    async def get_chat_summaries(username: str):
        try:
            return await deps.chat_service.list_chat_summaries(username)
        except BotNotFoundError:
            raise HTTPException(status_code=404, detail="Bot not found")

    @router.get(
        "/bots/{username}/chats/{chat_id}/messages",
        response_model=list[Message],
    )
    async def get_messages(username: str, chat_id: str):
        try:
            return await deps.chat_service.list_messages(username, chat_id)
        except BotNotFoundError:
            raise HTTPException(status_code=404, detail="Bot not found")

    @router.post(
        "/bots/{username}/chats/{chat_id}/messages/read",
        response_model=MarkThreadReadResponse,
    )
    async def mark_message_read(
        username: str, chat_id: str, payload: MarkThreadReadRequest
    ):
        try:
            marked_count = await deps.chat_service.mark_message_read(
                username, chat_id, payload.read_at
            )
        except BotNotFoundError:
            raise HTTPException(status_code=404, detail="Bot not found")
        except NoActiveConversationError:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return MarkThreadReadResponse(
            chat_id=chat_id,
            read_at=payload.read_at,
            marked_count=marked_count,
        )

    @router.post(
        "/bots/{username}/chats/{chat_id}/messages",
        response_model=Message,
    )
    async def post_message(
        username: str, chat_id: str, payload: SendMessageRequest
    ):
        try:
            return await deps.chat_service.send_message(
                username,
                payload.id,
                chat_id,
                payload.text,
                payload.timestamp,
            )
        except BotNotFoundError:
            raise HTTPException(status_code=404, detail="Bot not found")
        except NoActiveConversationError:
            raise HTTPException(
                status_code=409,
                detail="No active conversation for this chat_id — the participant must message the bot first",
            )

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await deps.connection_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await deps.connection_manager.disconnect(websocket)

    return router
