from __future__ import annotations

import pytest

from tests.helpers import admit_user_message


def _webhook_url(bot_id: str = "123456789") -> str:
    return f"/telegram/webhook/{bot_id}"


@pytest.mark.asyncio
async def test_webhook_rejects_bad_secret(http_client):
    client, ctx, _fake = http_client
    await admit_user_message(ctx.chat_service, chat_id="1")

    body = {
        "message": {
            "message_id": 2,
            "date": 1700000000,
            "text": "hello",
            "chat": {"id": 1},
        }
    }
    r = await client.post(
        _webhook_url(),
        json=body,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_webhook_accepts_valid_secret_stores_message(http_client):
    client, _ctx, _fake = http_client
    body = {
        "message": {
            "message_id": 42,
            "date": 1700000000,
            "text": "from webhook",
            "chat": {"id": 424242},
        }
    }
    r = await client.post(
        _webhook_url(),
        json=body,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    hist = await client.get("/bots/fixturebot/chats/424242/messages")
    assert hist.status_code == 200
    msgs = hist.json()
    assert len(msgs) == 1
    assert msgs[0]["text"] == "from webhook"
    assert msgs[0]["sender"] == "user"


@pytest.mark.asyncio
async def test_webhook_unknown_bot_returns_403(http_client):
    client, _ctx, _fake = http_client
    r = await client.post(
        "/telegram/webhook/999999999",
        json={"message": {"message_id": 1, "date": 1, "text": "x", "chat": {"id": 1}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
    )
    assert r.status_code == 403
