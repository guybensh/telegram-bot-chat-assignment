"""Concurrency smoke tests for the in-memory repository.

Run from backend/:
    python -m tests.test_repository_concurrency
"""

import asyncio
from datetime import datetime, timezone

from app.domain.chat.repository.in_memory_chat_repository import InMemoryChatRepository
from app.models import Message, Sender, Status

_BOT_ID = 1


def _message(message_id: str, chat_id: str) -> Message:
    return Message(
        id=message_id,
        bot_id=_BOT_ID,
        chat_id=chat_id,
        text=f"msg-{message_id}",
        timestamp=datetime.now(timezone.utc),
        sender=Sender.USER,
        status=Status.RECEIVED,
    )


async def test_concurrent_register_respects_capacity() -> None:
    repo = InMemoryChatRepository()

    async def try_register(chat_id: str) -> bool:
        if not await repo.register_chat(_BOT_ID, chat_id, max_chats=1):
            return False
        await repo.add_message(_BOT_ID, chat_id, _message(f"id-{chat_id}", chat_id))
        return True

    results = await asyncio.gather(
        *(try_register(str(chat_id)) for chat_id in range(50))
    )
    admitted = [str(chat_id) for chat_id, ok in enumerate(results) if ok]

    assert len(admitted) == 1
    assert await repo.active_chats(_BOT_ID) == admitted
    assert len(await repo.get_conversation(_BOT_ID, admitted[0])) == 1


async def test_concurrent_adds_preserve_all_messages() -> None:
    repo = InMemoryChatRepository()
    chat_id = "42"
    await repo.register_chat(_BOT_ID, chat_id, max_chats=1)

    async def add_one(index: int) -> None:
        await repo.add_message(_BOT_ID, chat_id, _message(f"msg-{index}", chat_id))

    await asyncio.gather(*(add_one(i) for i in range(100)))

    stored = await repo.get_conversation(_BOT_ID, chat_id)
    assert len(stored) == 100
    assert len({message.id for message in stored}) == 100


async def test_add_is_atomic_with_reset() -> None:
    repo = InMemoryChatRepository()
    chat_id = "7"
    await repo.register_chat(_BOT_ID, chat_id, max_chats=1)

    async def reset_loop() -> None:
        for _ in range(20):
            await repo.reset()
            await asyncio.sleep(0)

    async def send_loop() -> int:
        stored = 0
        for index in range(50):
            message = _message(f"out-{index}", chat_id)
            message.sender = Sender.AGENT
            message.status = Status.PENDING
            if await repo.add_message(_BOT_ID, chat_id, message) is not None:
                stored += 1
            await asyncio.sleep(0)
        return stored

    _, stored = await asyncio.gather(reset_loop(), send_loop())
    active = await repo.active_chats(_BOT_ID)
    if active:
        history = await repo.get_conversation(_BOT_ID, chat_id)
        assert all(message.id.startswith("out-") for message in history)
        assert len(history) <= stored


async def main() -> None:
    await test_concurrent_register_respects_capacity()
    await test_concurrent_adds_preserve_all_messages()
    await test_add_is_atomic_with_reset()
    print("concurrency checks passed")


if __name__ == "__main__":
    asyncio.run(main())
