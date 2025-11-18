import asyncio
import pytest

from core.bus import MessageBus
from core.message import Message, MessageType


@pytest.mark.asyncio
async def test_direct_dispatch_calls_handler_immediately():
    bus = MessageBus()

    called = asyncio.Event()

    async def handler(msg: Message):
        assert msg.content == "ping"
        called.set()
        return Message(
            message_type=MessageType.RESPONSE,
            sender_id="AgentX",
            content="pong",
            receiver_id=msg.sender_id,
        )

    bus.subscribe("AgentX", handler)

    msg = Message(
        message_type=MessageType.REQUEST,
        sender_id="Tester",
        content="ping",
        receiver_id="AgentX",
    )

    await bus.publish(msg, direct_dispatch=True)

    # Handler should have been called without starting the loop
    assert called.is_set()
    # Two messages recorded: original + response
    assert bus.get_message_count() == 2


@pytest.mark.asyncio
async def test_user_messages_are_queued_even_with_direct_dispatch():
    bus = MessageBus()

    called = False

    async def user_handler(msg: Message):
        nonlocal called
        called = True

    bus.subscribe("user", user_handler)

    msg = Message(
        message_type=MessageType.NOTIFICATION,
        sender_id="Planner",
        content="hello",
        receiver_id="user",
    )

    await bus.publish(msg, direct_dispatch=True)

    # Should not have dispatched directly; message queued instead
    assert called is False
    assert bus.queue.qsize() == 1
    assert bus.get_message_count() == 1
