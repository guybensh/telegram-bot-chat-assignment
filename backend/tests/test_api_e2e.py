from __future__ import annotations

import pytest

from tests.helpers import admit_user_message


@pytest.mark.asyncio
async def test_health_e2e(http_client):
    client, _ctx, _fake = http_client
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_bots_e2e(http_client):
    client, _ctx, _fake = http_client
    r = await client.get("/bots")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["username"] == "fixturebot"
    assert data[0]["active_chats"] == 0


@pytest.mark.asyncio
async def test_chat_summaries_unknown_bot_404(http_client):
    client, _ctx, _fake = http_client
    r = await client.get("/bots/unknownbot/chat-summaries")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_send_message_409_when_chat_not_active(http_client):
    client, _ctx, fake = http_client
    payload = {
        "id": "c1",
        "text": "hello",
        "timestamp": "2026-01-01T00:00:00+00:00",
    }
    r = await client.post(
        "/bots/fixturebot/chats/999/messages",
        json=payload,
    )
    assert r.status_code == 409
    assert fake.sent == []


@pytest.mark.asyncio
async def test_send_message_e2e_full_stack(http_client):
    client, ctx, fake = http_client
    await admit_user_message(ctx.chat_service, chat_id="111222")

    payload = {
        "id": "out-99",
        "text": "agent says hi",
        "timestamp": "2026-01-02T00:00:00+00:00",
    }
    r = await client.post(
        "/bots/fixturebot/chats/111222/messages",
        json=payload,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "sent"
    assert body["text"] == "agent says hi"
    assert fake.sent == [("123456789", "111222", "agent says hi")]

    hist = await client.get("/bots/fixturebot/chats/111222/messages")
    assert hist.status_code == 200
    msgs = hist.json()
    assert len(msgs) == 2
    ids = {m["id"] for m in msgs}
    assert "out-99" in ids
    assert any(m["id"] == "out-99" and m["status"] == "sent" for m in msgs)


@pytest.mark.asyncio
async def test_mark_read_404_unknown_chat(http_client):
    client, _ctx, _fake = http_client
    r = await client.post(
        "/bots/fixturebot/chats/999/messages/read",
        json={"read_at": "2026-06-01T00:00:00+00:00"},
    )
    assert r.status_code == 404
