import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks active WebSocket clients and broadcasts server-push events.

    The client uses the socket purely as a receive channel (it sends via REST),
    so we only ever push. Multiple browser tabs map to multiple sockets and all
    stay in sync via broadcast.
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
