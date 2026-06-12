import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks connected agent clients and broadcasts server-push events.

    A client uses the socket purely as a receive channel (it sends via REST),
    so we only ever push. Events carry their own `chat_id`, so a client routes
    each one to the right conversation; with one agent console, broadcasting to
    every connected client keeps all tabs in sync.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    def has_clients(self) -> bool:
        """Whether any agent is currently connected. Used to gate incoming
        messages — don't accept a conversation when no agent is there."""
        return bool(self._connections)

    async def broadcast(self, event: dict) -> None:
        async with self._lock:
            targets = list(self._connections)
        # Send outside the lock; drop any socket that errors mid-send.
        for websocket in targets:
            try:
                await websocket.send_json(event)
            except Exception:
                logger.info("Dropping unresponsive WebSocket client")
                await self.disconnect(websocket)
