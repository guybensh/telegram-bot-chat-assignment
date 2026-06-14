from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ..bot import BotNotFoundError
from ..bot.record import BotRecord
from ..chat import NoActiveConversationError
from ..deps import Dependencies
from ..models import ConversationSummary, Message, SendMessageRequest

router = APIRouter()


def register_routes(deps: Dependencies) -> APIRouter:
    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.post("/admin/reset")
    async def admin_reset():
        await deps.chat.reset()
        return {"status": "reset"}

    @router.get("/bots", response_model=list[BotRecord])
    async def get_bots():
        return await deps.bot_service.list_bots()

    @router.get(
        "/bots/{username}/conversations",
        response_model=list[ConversationSummary],
    )
    async def get_bot_conversations(username: str):
        try:
            return await deps.chat.list_conversation_summaries(username)
        except BotNotFoundError:
            raise HTTPException(status_code=404, detail="Bot not found")

    @router.get("/bots/{username}/messages", response_model=list[Message])
    async def get_messages(username: str, chat_id: int):
        try:
            return await deps.chat.get_history(username, chat_id)
        except BotNotFoundError:
            raise HTTPException(status_code=404, detail="Bot not found")

    @router.post("/bots/{username}/messages", response_model=Message)
    async def post_message(username: str, payload: SendMessageRequest):
        try:
            return await deps.chat.send_message(
                username,
                payload.id,
                payload.chat_id,
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
