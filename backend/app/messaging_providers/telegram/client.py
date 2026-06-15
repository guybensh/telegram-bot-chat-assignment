import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramClient:
    """Stateless Telegram Bot HTTP client — one shared transport, token per call."""

    def __init__(self, api_base: str, *, mock: bool = False) -> None:
        self._api_base = api_base
        self._mock = mock
        # Read timeout must exceed the long-poll timeout used in get_updates.
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(40.0))

    def _url(self, token: str, method: str) -> str:
        return f"{self._api_base}/bot{token}/{method}"

    async def close(self) -> None:
        await self._http.aclose()

    async def get_me(self, token: str) -> dict | None:
        """Fetch bot profile metadata (name, username) via getMe."""
        if self._mock:
            return None
        try:
            resp = await self._http.get(self._url(token, "getMe"))
            data = resp.json()
            if data.get("ok"):
                return data.get("result")
        except Exception:
            logger.exception("[TelegramClient::get_me]: getMe failed")
        return None

    async def send_message(self, token: str, chat_id: int, text: str) -> bool:
        if self._mock:
            logger.info(
                "[TelegramClient::send_message]: Mock mode: simulating successful Telegram delivery"
            )
            return True
        try:
            resp = await self._http.post(
                self._url(token, "sendMessage"),
                json={"chat_id": chat_id, "text": text},
            )
            return bool(resp.json().get("ok"))
        except Exception:
            logger.exception("[TelegramClient::send_message]: sendMessage failed")
            return False

    async def get_updates(
        self, token: str, offset: int, timeout: int = 30
    ) -> list[dict] | None:
        """Long-poll for updates.

        Returns the (possibly empty) list of updates on success, or None on
        error — e.g. a 409 Conflict when another instance is polling the same
        bot. The caller distinguishes None to back off instead of hammering.
        """
        try:
            resp = await self._http.get(
                self._url(token, "getUpdates"),
                params={"offset": offset, "timeout": timeout},
            )
            if resp.status_code != 200:
                logger.warning(
                    "[TelegramClient::get_updates]: getUpdates HTTP %s: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
            data = resp.json()
            return data.get("result", []) if data.get("ok") else None
        except Exception:
            logger.exception("[TelegramClient::get_updates]: getUpdates failed")
            return None

    async def set_webhook(
        self, token: str, url: str, secret: str | None = None
    ) -> bool:
        payload: dict = {"url": url}
        if secret:
            payload["secret_token"] = secret
        try:
            resp = await self._http.post(
                self._url(token, "setWebhook"), json=payload
            )
            return bool(resp.json().get("ok"))
        except Exception:
            logger.exception("[TelegramClient::set_webhook]: setWebhook failed")
            return False

    async def delete_webhook(self, token: str) -> bool:
        try:
            resp = await self._http.post(self._url(token, "deleteWebhook"))
            return bool(resp.json().get("ok"))
        except Exception:
            logger.exception("[TelegramClient::delete_webhook]: deleteWebhook failed")
            return False
