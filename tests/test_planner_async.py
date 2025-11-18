import pytest

from core.message import Message, MessageType
from core.planner import Planner
from core.registry import Registry
from core.bus import MessageBus
from learning.router_learner import RouterLearner
from memory.society_memory import SocietyMemory


@pytest.mark.asyncio
async def test_planner_missing_capability_triggers_agent_creation(tmp_path):
    # Set up minimal planner environment with empty registry
    bus = MessageBus()
    registry = Registry()
    learner = RouterLearner(registry)
    memory = SocietyMemory()
    planner = Planner(
        registry=registry, message_bus=bus, router_learner=learner, society_memory=memory
    )

    # Use a user request that maps to a known task_type but with no candidates
    msg = Message(
        message_type=MessageType.REQUEST,
        sender_id="user",
        content="Import all new books from my Android downloads",
    )

    response = await planner.receive_message(msg)

    # Should respond to user indicating agent creation path
    assert response is not None
    assert response.receiver_id == "user"
    assert "create a new agent" in response.content.lower()
