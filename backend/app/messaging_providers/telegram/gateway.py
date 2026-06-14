import logging

from .api import TelegramAPI

logger = logging.getLogger(__name__)


class TelegramGateway:
    """Multi-bot Telegram I/O — one API client per token, created on demand."""

    def __init__(self, api_base: str, *, mock: bool = False) -> None:
        self._api_base = api_base
        self._mock = mock
        self._clients: dict[str, TelegramAPI] = {}

    def client_for(self, token: str) -> TelegramAPI:
        if token not in self._clients:
            self._clients[token] = TelegramAPI(token, self._api_base)
        return self._clients[token]

    async def close(self) -> None:
        for client in self._clients.values():
            await client.close()
        self._clients.clear()

    async def send(self, token: str, chat_id: int, text: str) -> bool:
        if self._mock:
            logger.info("Mock mode: simulating successful Telegram delivery")
            return True
        return await self.client_for(token).send_message(chat_id, text)

    async def get_me(self, token: str) -> dict | None:
        if self._mock:
            return None
        return await self.client_for(token).get_me()

    async def get_updates(
        self, token: str, offset: int, timeout: int = 30
    ) -> list[dict] | None:
        return await self.client_for(token).get_updates(offset, timeout)

    async def set_webhook(
        self, token: str, url: str, secret: str | None = None
    ) -> bool:
        return await self.client_for(token).set_webhook(url, secret)

    async def delete_webhook(self, token: str) -> bool:
        return await self.client_for(token).delete_webhook()
