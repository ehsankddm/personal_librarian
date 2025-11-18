import asyncio
import os
from pathlib import Path

import pytest

from core.message import Message, MessageType
from core.bus import MessageBus
from core.registry import Registry
from core.planner import Planner
from learning.router_learner import RouterLearner
from memory.society_memory import SocietyMemory
from learning.telemetry_collector import TelemetryCollector
from agents.planner_agent import PlannerAgent
from agents.gatekeeper_agent import GatekeeperAgent
from agents.code_generator_agent import CodeGeneratorAgent
from core.preferences import PreferenceManager
from core.policies import PolicyManager
from core.gatekeeper import Gatekeeper
from actions.executor import ActionExecutor
from memory.memory_log import MemoryLog


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Ensure base folders exist similar to dev run
    for p in [
        "logs",
        "state",
        "memory/agents",
        "memory/society",
        "agents_generated_specs/requested_capabilities",
        "agents_generated_specs/accepted",
        "agents_generated_specs/drafts",
        "agents/dynamic",
    ]:
        Path(p).mkdir(parents=True, exist_ok=True)
    yield


@pytest.mark.asyncio
async def test_planner_llm_decision_and_telemetry(monkeypatch, tmp_path):
    # Setup telemetry DB under tmp
    tel = TelemetryCollector(db_path=str(Path("state/telemetry.db")))

    # Monkeypatch LLMClient to deterministic response
    from core import llm_client as llmc

    async def fake_generate_reasoning(self, context_bundle, system_prompt, tools=None, model=None, temperature=0.0, max_tokens=256):
        return {
            "raw_text": "{\n\"chosen_route\": \"Ask user for clarification\", \n\"justification\": \"Ambiguous\", \n\"confidence\": 0.7, \n\"needs_user_confirmation\": true\n}",
            "parsed_json": {
                "chosen_route": "Ask user for clarification",
                "justification": "Ambiguous",
                "confidence": 0.7,
                "needs_user_confirmation": True,
            },
            "finish_reason": "stop",
            "tokens_in": 10,
            "tokens_out": 30,
            "model_name": "test-model",
            "elapsed_ms": 12,
        }

    monkeypatch.setattr(llmc.LLMClient, "generate_reasoning", fake_generate_reasoning)

    # Minimal agent for calling reason_with_llm
    bus = MessageBus(telemetry_collector=tel)
    pref = PreferenceManager()
    pol = PolicyManager()
    agent = PlannerAgent(
        agent_id="PlannerAgent_main_v1",
        role="PlannerAgent",
        name="Main Planner Agent",
        planner=None,
        registry=Registry(),
        message_bus=bus,
        preferences=pref,
        policies=pol,
        telemetry_collector=tel,
        memory_log=MemoryLog(),
        gatekeeper=Gatekeeper(pol, ActionExecutor()),
    )

    llm_ctx = agent.build_llm_context(None)
    decision = await agent.reason_with_llm(llm_ctx)

    assert decision["chosen_route"].startswith("Ask user")
    # Telemetry events recorded
    import sqlite3

    conn = sqlite3.connect("state/telemetry.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM telemetry WHERE action IN ('llm_prompt','llm_response')")
    count = cur.fetchone()[0]
    conn.close()
    assert count >= 2


@pytest.mark.asyncio
async def test_planner_llm_ask_user_fields(monkeypatch, tmp_path):
    # Mock LLM to include ask_user_clarification and clarification_prompt
    from core import llm_client as llmc

    async def fake_generate_reasoning(self, context_bundle, system_prompt, tools=None, model=None, temperature=0.0, max_tokens=256):
        return {
            "raw_text": "{\n  \"chosen_route\": \"Ask user for clarification\",\n  \"justification\": \"Need a source folder\",\n  \"confidence\": 0.65,\n  \"needs_user_confirmation\": true,\n  \"ask_user_clarification\": true,\n  \"clarification_prompt\": \"Which folder contains your books?\"\n}",
            "parsed_json": {
                "chosen_route": "Ask user for clarification",
                "justification": "Need a source folder",
                "confidence": 0.65,
                "needs_user_confirmation": True,
                "ask_user_clarification": True,
                "clarification_prompt": "Which folder contains your books?",
            },
            "finish_reason": "stop",
            "tokens_in": 10,
            "tokens_out": 30,
            "model_name": "test-model",
            "elapsed_ms": 9,
        }

    monkeypatch.setattr(llmc.LLMClient, "generate_reasoning", fake_generate_reasoning)

    tel = TelemetryCollector(db_path=str(Path("state/telemetry.db")))
    bus = MessageBus(telemetry_collector=tel)
    agent = PlannerAgent(
        agent_id="PlannerAgent_main_v1",
        role="PlannerAgent",
        name="Main Planner Agent",
        planner=None,
        registry=Registry(),
        message_bus=bus,
        preferences=PreferenceManager(),
        policies=PolicyManager(),
        telemetry_collector=tel,
        memory_log=MemoryLog(),
        gatekeeper=Gatekeeper(PolicyManager(), ActionExecutor()),
    )

    decision = await agent.reason_with_llm(agent.build_llm_context(None))
    assert decision["needs_user_confirmation"] is True
    assert decision["justification"]


@pytest.mark.asyncio
async def test_codegen_scaffold_and_manifest(monkeypatch):
    # Set up core components
    tel = TelemetryCollector(db_path=str(Path("state/telemetry.db")))
    bus = MessageBus(telemetry_collector=tel)
    reg = Registry()
    learner = RouterLearner(reg)
    soc = SocietyMemory()
    planner = Planner(registry=reg, message_bus=bus, router_learner=learner, society_memory=soc)

    pol = PolicyManager()
    gate = Gatekeeper(pol, ActionExecutor())

    # Agents
    codegen = CodeGeneratorAgent(
        agent_id="CodeGeneratorAgent_main_v1",
        role="CodeGeneratorAgent",
        name="CodeGen",
        registry=reg,
        message_bus=bus,
        preferences=PreferenceManager(),
        policies=pol,
        telemetry_collector=tel,
        memory_log=MemoryLog(),
        gatekeeper=gate,
    )

    bus.subscribe("CodeGeneratorAgent_main_v1", codegen.handle)
    bus.subscribe("CodeGeneratorAgent", codegen.handle)

    # Simulate missing capability via Planner
    user_msg = Message(message_type=MessageType.REQUEST, sender_id="user", content="Import all new books from my Android downloads")
    # Start bus loop
    task = asyncio.create_task(bus.start())
    try:
        await planner.receive_message(user_msg)
        # Allow time for CodeGeneratorAgent to process
        await asyncio.sleep(0.2)
    finally:
        bus.stop()
        with contextlib.suppress(Exception):
            await task

    # Assert files created
    drafts = list(Path("agents_generated_specs/drafts").glob("*.md"))
    manifests = list(Path("agents/dynamic").glob("*/MANIFEST.json"))
    assert drafts, "No draft spec created"
    assert manifests, "No scaffold manifest created"


@pytest.mark.asyncio
async def test_gatekeeper_advisory_and_telemetry(monkeypatch):
    from core import llm_client as llmc

    async def fake_generate_reasoning(self, context_bundle, system_prompt, tools=None, model=None, temperature=0.0, max_tokens=256):
        return {
            "raw_text": "{\"risk_summary\":\"Low risk\",\"policy_refs\":[\"net\"],\"suggested_decision\":\"approve\",\"user_prompt\":\"OK?\"}",
            "parsed_json": {
                "risk_summary": "Low risk",
                "policy_refs": ["net"],
                "suggested_decision": "approve",
                "user_prompt": "OK?",
            },
            "finish_reason": "stop",
            "tokens_in": 10,
            "tokens_out": 20,
            "model_name": "test-model",
            "elapsed_ms": 5,
        }

    monkeypatch.setattr(llmc.LLMClient, "generate_reasoning", fake_generate_reasoning)

    tel = TelemetryCollector(db_path=str(Path("state/telemetry.db")))
    pol = PolicyManager()
    gate = Gatekeeper(pol, ActionExecutor())
    agent = GatekeeperAgent(
        agent_id="GatekeeperAgent_main_v1",
        role="GatekeeperAgent",
        name="GK",
        gatekeeper=gate,
        registry=Registry(),
        message_bus=MessageBus(telemetry_collector=tel),
        preferences=PreferenceManager(),
        policies=pol,
        telemetry_collector=tel,
        memory_log=MemoryLog(),
    )

    from actions.action_request import ActionRequest, ActionType

    advisory = await agent.advise_on(ActionRequest(requester_agent_id="X", requester_role="R", action_type=ActionType.NETWORK_FETCH))
    assert advisory["suggested_decision"] == "approve"

    # Telemetry exists
    import sqlite3

    conn = sqlite3.connect("state/telemetry.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM telemetry WHERE action IN ('llm_prompt','llm_response') AND agent_id='GatekeeperAgent_main_v1'")
    count = cur.fetchone()[0]
    conn.close()
    assert count >= 2


import contextlib


@pytest.mark.asyncio
async def test_approve_load_and_activate_dynamic_agent(monkeypatch, tmp_path):
    # Prepare a fake generated agent scaffold + manifest
    agent_name = "TestAgent_v1"
    base = Path("agents/dynamic") / agent_name
    base.mkdir(parents=True, exist_ok=True)
    (base / "__init__.py").write_text("\n")
    module = base / f"{agent_name.lower()}.py"
    module.write_text(
        """
from typing import Optional
from agents.agent_core import Agent
from core.message import Message, MessageType


class TestAgent_v1(Agent):
    async def can_handle(self, message: Message) -> bool:
        return False

    async def handle(self, message: Message) -> Optional[Message]:
        return None

    def describe_capabilities(self) -> str:
        return "Scaffold for TestAgent_v1"
""".lstrip()
    )

    manifest = {
        "agent_name": agent_name,
        "files": [{"path": str(module), "sha256": "", "mode": "text"}],
        "spec_path": "agents_generated_specs/drafts/draft_dummy.md",
        "generated_by": "CodeGeneratorAgent_main_v1",
        "created_at": "2025-01-01T00:00:00Z",
        "self_test_cmd": "pytest -q",
    }
    man_path = base / "MANIFEST.json"
    man_path.write_text(__import__("json").dumps(manifest, indent=2))

    # Core setup
    tel = TelemetryCollector(db_path=str(Path("state/telemetry.db")))
    bus = MessageBus(telemetry_collector=tel)
    reg = Registry()
    learner = RouterLearner(reg)
    soc = SocietyMemory()
    planner = Planner(registry=reg, message_bus=bus, router_learner=learner, society_memory=soc)
    pol = PolicyManager()
    gate = Gatekeeper(pol, ActionExecutor())

    # Planner agent
    planner_agent = PlannerAgent(
        agent_id="PlannerAgent_main_v1",
        role="PlannerAgent",
        name="Main Planner Agent",
        planner=planner,
        registry=reg,
        message_bus=bus,
        preferences=PreferenceManager(),
        policies=pol,
        telemetry_collector=tel,
        memory_log=MemoryLog(),
        gatekeeper=gate,
    )

    # Step 1: Approve load
    msg_load = Message(
        message_type=MessageType.REQUEST,
        sender_id="user",
        content=f"approve load {man_path}",
    )
    await planner_agent.handle(msg_load)

    # Registry should now contain quarantined entry
    info = reg.get_agent(agent_name)
    assert info is not None and info.status == "quarantined"

    # Step 2: Activate agent
    msg_activate = Message(
        message_type=MessageType.REQUEST,
        sender_id="user",
        content=f"activate agent {agent_name}",
    )
    await planner_agent.handle(msg_activate)

    # Registry status should be active and bus should have a subscription
    info2 = reg.get_agent(agent_name)
    assert info2 is not None and info2.status == "active" and info2.alive is True
    assert agent_name in bus.subscribers
