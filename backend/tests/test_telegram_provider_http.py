from __future__ import annotations

import json
from datetime import datetime, timezone

import respx
from httpx import Response

from tests.helpers import admit_user_message


@respx.mock
async def test_send_message_calls_telegram_api(telegram_app_context):
    ctx, _provider = telegram_app_context
    await admit_user_message(ctx.chat_service, chat_id="777")

    token = "TEST_TOKEN_FIXTURE"
    route = respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        return_value=Response(200, json={"ok": True, "result": {}})
    )

    out = await ctx.chat_service.send_message(
        "fixturebot",
        "m1",
        "777",
        "payload text",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert out.status.value == "sent"
    assert route.called
    sent = route.calls.last.request
    assert sent is not None
    body = json.loads(sent.content.decode())
    assert body["chat_id"] == 777
    assert body["text"] == "payload text"


@respx.mock
async def test_send_message_telegram_returns_ok_false(telegram_app_context):
    ctx, _ = telegram_app_context
    await admit_user_message(ctx.chat_service, chat_id="888")

    token = "TEST_TOKEN_FIXTURE"
    respx.post(f"https://api.telegram.org/bot{token}/sendMessage").mock(
        return_value=Response(200, json={"ok": False})
    )

    out = await ctx.chat_service.send_message(
        "fixturebot",
        "m2",
        "888",
        "x",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert out.status.value == "failed"


@respx.mock
async def test_fetch_bot_profile_get_me(telegram_app_context):
    _ctx, provider = telegram_app_context
    token = "TEST_TOKEN_FIXTURE"
    respx.get(f"https://api.telegram.org/bot{token}/getMe").mock(
        return_value=Response(
            200,
            json={
                "ok": True,
                "result": {
                    "id": 123456789,
                    "is_bot": True,
                    "first_name": "Fixture",
                    "username": "fixturebot",
                },
            },
        )
    )
    profile = await provider.fetch_bot_profile("123456789")
    assert profile is not None
    assert profile.username == "fixturebot"
