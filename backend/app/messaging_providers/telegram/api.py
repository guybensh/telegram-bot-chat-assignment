import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramAPI:
    """Thin async wrapper over the Telegram Bot HTTP API.

    No business logic — just the handful of endpoints we use, each returning a
    simple result and swallowing transport errors so callers can stay clean.
    """

    def __init__(self, token: str, api_base: str) -> None:
        self._base = f"{api_base}/bot{token}"
        # Read timeout must exceed the long-poll timeout used in get_updates.
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(40.0))

    async def close(self) -> None:
        await self._client.aclose()

    async def get_me(self) -> dict | None:
        """Fetch bot profile metadata (name, username) via getMe."""
        try:
            resp = await self._client.get(f"{self._base}/getMe")
            data = resp.json()
            if data.get("ok"):
                return data.get("result")
        except Exception:
            logger.exception("getMe failed")
        return None

    async def send_message(self, chat_id: int, text: str) -> bool:
        try:
            resp = await self._client.post(
                f"{self._base}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            return bool(resp.json().get("ok"))
        except Exception:
            logger.exception("sendMessage failed")
            return False

    async def get_updates(self, offset: int, timeout: int = 30) -> list[dict] | None:
        """Long-poll for updates.

        Returns the (possibly empty) list of updates on success, or None on
        error — e.g. a 409 Conflict when another instance is polling the same
        bot. The caller distinguishes None to back off instead of hammering.
        """
        try:
            resp = await self._client.get(
                f"{self._base}/getUpdates",
                params={"offset": offset, "timeout": timeout},
            )
            if resp.status_code != 200:
                logger.warning("getUpdates HTTP %s: %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            return data.get("result", []) if data.get("ok") else None
        except Exception:
            logger.exception("getUpdates failed")
            return None

    async def set_webhook(self, url: str, secret: str | None = None) -> bool:
        payload: dict = {"url": url}
        if secret:
            payload["secret_token"] = secret
        try:
            resp = await self._client.post(f"{self._base}/setWebhook", json=payload)
            return bool(resp.json().get("ok"))
        except Exception:
            logger.exception("setWebhook failed")
            return False

    async def delete_webhook(self) -> bool:
        try:
            resp = await self._client.post(f"{self._base}/deleteWebhook")
            return bool(resp.json().get("ok"))
        except Exception:
            logger.exception("deleteWebhook failed")
            return False
