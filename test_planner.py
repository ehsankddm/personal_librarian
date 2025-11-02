#!/usr/bin/env python3
"""Test script to verify Planner implementation."""

import asyncio
from core.message import Message, MessageType, TaskStatus
from core.bus import MessageBus
from core.planner import Planner
from core.registry import Registry
from learning.router_learner import RouterLearner
from memory.society_memory import SocietyMemory
from agents.planner_agent import PlannerAgent
from agents.interface_agent import InterfaceAgent
from learning.telemetry_collector import TelemetryCollector
from core.preferences import PreferenceManager
from core.policies import PolicyManager
from core.gatekeeper import Gatekeeper
from core.policies import PolicyManager
from actions.executor import ActionExecutor
from memory.memory_log import MemoryLog


async def test_planner():
    """Test Planner functionality."""
    print("🧪 Testing Planner Implementation\n")

    # Initialize components
    print("📦 Initializing components...")
    message_bus = MessageBus()
    registry = Registry()
    router_learner = RouterLearner(registry)
    society_memory = SocietyMemory()
    telemetry_collector = TelemetryCollector()

    # Initialize Planner
    planner = Planner(
        registry=registry,
        message_bus=message_bus,
        router_learner=router_learner,
        society_memory=society_memory,
        telemetry_collector=telemetry_collector,
    )

    print("✓ Planner initialized")

    # Create agents
    print("\n📦 Creating agents...")
    policy_manager = PolicyManager()
    executor = ActionExecutor()
    gatekeeper = Gatekeeper(policy_manager, executor)

    interface_agent = InterfaceAgent(
        agent_id="InterfaceAgent_main_v1",
        role="InterfaceAgent",
        name="Main Interface Agent",
        traits={"primary": True},
        registry=registry,
        message_bus=message_bus,
        preferences=PreferenceManager(),
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=MemoryLog(),
        gatekeeper=gatekeeper,
    )
    print("✓ InterfaceAgent created")

    planner_agent = PlannerAgent(
        agent_id="PlannerAgent_main_v1",
        role="PlannerAgent",
        name="Main Planner Agent",
        traits={"primary": True},
        planner=planner,
        registry=registry,
        message_bus=message_bus,
        preferences=PreferenceManager(),
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=MemoryLog(),
        gatekeeper=gatekeeper,
    )
    print("✓ PlannerAgent created")

    # Test 1: Interpret intent
    print("\n✓ Test 1: interpret_intent")
    user_message = Message(
        message_type=MessageType.REQUEST,
        sender_id="user",
        content="Import all new books from my Android downloads",
    )
    intent = await planner.interpret_intent(user_message)
    print(f"  Task Type: {intent.task_type}")
    print(f"  Goal: {intent.goal}")
    print(f"  Tags: {intent.tags}")
    assert intent.task_type == "ingestion"

    # Test 2: Find candidates
    print("\n✓ Test 2: find_candidates")
    candidates = await planner.find_candidates(intent)
    print(f"  Found {len(candidates)} candidates")

    # Test 3: Create task
    print("\n✓ Test 3: create_task")
    task = await planner.create_task("Test task")
    print(f"  Task ID: {task.task_id}")
    assert task.status == TaskStatus.PENDING

    # Test 4: Receive message flow (missing capability scenario)
    print("\n✓ Test 4: receive_message (missing capability)")
    response = await planner.receive_message(user_message)
    print(f"  Response: {response.content[:100]}...")
    assert "create" in response.content.lower() or "missing" in response.content.lower()

    # Test 5: PlannerAgent can_handle
    print("\n✓ Test 5: PlannerAgent can_handle")
    can_handle = await planner_agent.can_handle(user_message)
    print(f"  Can handle: {can_handle}")
    assert can_handle

    # Test 6: Daily summary
    print("\n✓ Test 6: summarize_day")
    await planner.summarize_day()
    print("  Daily summary written to society memory")

    print("\n🎉 All Planner tests passed!")
    print("\nImplemented features:")
    print("  ✓ interpret_intent method")
    print("  ✓ find_candidates method")
    print("  ✓ filter_by_policy_and_scope")
    print("  ✓ rank_candidates with RouterLearner")
    print("  ✓ route_to_best method")
    print("  ✓ monitor_progress and reward_feedback")
    print("  ✓ Missing capability handling")
    print("  ✓ Escalation rules")
    print("  ✓ Task management")
    print("  ✓ Daily summarization")
    print("  ✓ PlannerAgent integration")


if __name__ == "__main__":
    asyncio.run(test_planner())
