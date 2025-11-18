#!/usr/bin/env python3
"""
Development entry point for Personal Librarian.
Starts the minimal viable society (MVS) per Phase 0.
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from actions.executor import ActionExecutor
from agents.code_generator_agent import CodeGeneratorAgent
from agents.curator_agent import CuratorAgent
from agents.gatekeeper_agent import GatekeeperAgent
from agents.interface_agent import InterfaceAgent

# Agents
from agents.planner_agent import PlannerAgent
from agents.reflection_agent import ReflectionAgent

# Core imports
from core.bus import MessageBus
from core.gatekeeper import Gatekeeper
from core.message import Message, MessageType
from core.planner import Planner
from core.policies import PolicyManager
from core.preferences import PreferenceManager
from core.registry import Registry

# Learning and memory
from learning.router_learner import RouterLearner
from learning.telemetry_collector import TelemetryCollector
from memory.memory_log import MemoryLog
from memory.society_memory import SocietyMemory

# Configure logging
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/runtime.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def main():
    """Start the MVS."""
    logger.info("Starting Personal Librarian MVS (Phase 0)...")
    # Load environment variables from .env file if present, before anything else
    load_dotenv()

    # Ensure necessary directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("state").mkdir(exist_ok=True)
    Path("memory/agents").mkdir(parents=True, exist_ok=True)
    Path("memory/society").mkdir(parents=True, exist_ok=True)
    Path("memory/archives").mkdir(parents=True, exist_ok=True)
    Path("agents_generated_specs/requested_capabilities").mkdir(parents=True, exist_ok=True)
    Path("agents_generated_specs/accepted").mkdir(parents=True, exist_ok=True)
    Path("agents_generated_specs/drafts").mkdir(parents=True, exist_ok=True)

    logger.info("Initializing core components...")

    # Initialize core infrastructure
    registry = Registry()
    router_learner = RouterLearner(registry)
    society_memory = SocietyMemory()
    telemetry_collector = TelemetryCollector()
    message_bus = MessageBus(telemetry_collector=telemetry_collector)
    policy_manager = PolicyManager()
    preference_manager = PreferenceManager()

    # Initialize learning and memory
    memory_log = MemoryLog()

    # Initialize Gatekeeper and Planner
    executor = ActionExecutor()
    gatekeeper = Gatekeeper(policy_manager, executor)
    planner = Planner(
        registry=registry,
        message_bus=message_bus,
        router_learner=router_learner,
        society_memory=society_memory,
        telemetry_collector=telemetry_collector,
    )

    logger.info("Creating agents...")

    # Create agents
    planner_agent = PlannerAgent(
        agent_id="PlannerAgent_main_v1",
        role="PlannerAgent",
        name="Main Planner Agent",
        traits={"primary": True},
        planner=planner,
        registry=registry,
        message_bus=message_bus,
        preferences=preference_manager,
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=memory_log,
        gatekeeper=gatekeeper,
        society_memory=society_memory,
        bus=message_bus,
        logger=logger,
    )

    gatekeeper_agent = GatekeeperAgent(
        agent_id="GatekeeperAgent_main_v1",
        role="GatekeeperAgent",
        name="Main Gatekeeper Agent",
        traits={"primary": True},
        gatekeeper=gatekeeper,
        registry=registry,
        message_bus=message_bus,
        preferences=preference_manager,
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=memory_log,
        logger=logger,
    )

    interface_agent = InterfaceAgent(
        agent_id="InterfaceAgent_main_v1",
        role="InterfaceAgent",
        name="Main Interface Agent",
        traits={"primary": True},
        registry=registry,
        message_bus=message_bus,
        preferences=preference_manager,
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=memory_log,
        gatekeeper=gatekeeper,
        logger=logger,
    )

    curator_agent = CuratorAgent(
        agent_id="CuratorAgent_main_v1",
        role="CuratorAgent",
        name="Main Curator Agent",
        traits={"primary": True},
        registry=registry,
        message_bus=message_bus,
        preferences=preference_manager,
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=memory_log,
        gatekeeper=gatekeeper,
        logger=logger,
    )

    code_generator_agent = CodeGeneratorAgent(
        agent_id="CodeGeneratorAgent_main_v1",
        role="CodeGeneratorAgent",
        name="Main Code Generator Agent",
        traits={"primary": True},
        registry=registry,
        message_bus=message_bus,
        preferences=preference_manager,
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=memory_log,
        gatekeeper=gatekeeper,
        logger=logger,
    )

    reflection_agent = ReflectionAgent(
        agent_id="ReflectionAgent_main_v1",
        role="ReflectionAgent",
        name="Main Reflection Agent",
        traits={"primary": True},
        registry=registry,
        message_bus=message_bus,
        preferences=preference_manager,
        policies=policy_manager,
        telemetry_collector=telemetry_collector,
        memory_log=memory_log,
        gatekeeper=gatekeeper,
        logger=logger,
    )

    logger.info("Registering agents with Registry...")

    # Register all agents
    agents = [
        planner_agent,
        gatekeeper_agent,
        interface_agent,
        curator_agent,
        code_generator_agent,
        reflection_agent,
    ]

    for agent in agents:
        # Avoid duplicate registrations across dev runs
        if registry.get_agent(agent.agent_id):
            logger.info(f"Agent already registered: {agent.agent_id}, skipping register")
            continue
        registry.register_agent(
            agent_id=agent.agent_id,
            role=agent.role,
            capabilities_summary=agent.describe_capabilities(),
            traits=agent.traits,
            instinct_paths=agent.instinct_paths,
            society_memory=society_memory,
        )

    logger.info(f"Registered {len(agents)} agents in Registry")

    # Subscribe agents to message bus
    logger.info("Subscribing agents to message bus...")

    for agent in agents:
        message_bus.subscribe(agent.agent_id, agent.handle)

    # Also subscribe Planner under "Planner" alias for messages
    message_bus.subscribe("Planner", planner_agent.handle)

    # Also subscribe InterfaceAgent under "InterfaceAgent" and "user" aliases
    message_bus.subscribe("InterfaceAgent", interface_agent.handle)
    message_bus.subscribe("user", interface_agent.handle)
    message_bus.subscribe("User", interface_agent.handle)

    # Subscribe CodeGeneratorAgent under role alias
    message_bus.subscribe("CodeGeneratorAgent", code_generator_agent.handle)

    logger.info("Message bus subscriptions complete")

    # Start message bus
    logger.info("Starting message bus...")
    asyncio.create_task(message_bus.start())

    # Log startup
    society_memory.add_entry(
        f"Personal Librarian MVS booted successfully with {len(agents)} agents. "
        f"Phase 0 kernel operational."
    )

    logger.info("=== Personal Librarian MVS Ready ===")
    logger.info("Agents loaded with instinct files:")
    for agent in agents:
        logger.info(
            f"  - {agent.agent_id}: {len(agent.instinct_paths)} instinct files, "
            f"{len(agent.instinct_text)} chars of behavior DNA"
        )

    # Interactive mode default: on (set INTERACTIVE=0 to disable)
    interactive_env = os.environ.get("INTERACTIVE", "1").strip().lower()
    interactive_mode = interactive_env not in {"0", "false", "no"}

    # Initialize placeholder for last user message (may be None in interactive mode)
    user_message: Message | None = None

    if not interactive_mode:
        # Test: Simulate one user request to prove "society is alive"
        logger.info("\n=== Testing Society Communication ===")
        logger.info("Simulating user request: 'Import all new books from my Android downloads'")

        user_message = Message(
            message_type=MessageType.REQUEST,
            sender_id="user",
            content="Import all new books from my Android downloads",
            receiver_id=None,
        )

        # Send through InterfaceAgent
        print("\n[User] Import all new books from my Android downloads\n")
        await interface_agent.handle(user_message)

        # Give agents time to process
        await asyncio.sleep(0.5)

    # Phase 1: Print LLM context bundles in dev mode
    phase1_mode = os.environ.get("PHASE1_DEV") == "1"

    if phase1_mode:
        logger.info("\n=== Phase 1: LLM Context Bundles ===")

        # Print Planner routing bundle
        print(f"\n--- LLM CONTEXT ({planner_agent.agent_id}) ---", flush=True)

        # Get a planner context bundle (would have been built during handle)
        # For demo or interactive, generate from the last message if available
        planner_context = planner_agent.build_llm_context(user_message)
        print("agent_identity.role:", planner_context["agent_identity"]["role"], flush=True)
        print("agent_identity.agent_id:", planner_context["agent_identity"]["agent_id"], flush=True)
        print(
            "task_hypothesis:", planner_context.get("task_hypothesis", "No hypothesis"), flush=True
        )
        print("candidate_actions:", planner_context.get("candidate_actions", []), flush=True)
        print(
            "escalation_policy:", planner_context.get("escalation_policy", "No policy"), flush=True
        )
        print(
            "questions_for_reasoner:", planner_context.get("questions_for_reasoner", []), flush=True
        )

        # Optional: Print Gatekeeper bundle if any action was evaluated
        # For Phase 1 demo, we'll skip this if no ActionRequest occurred
        print(flush=True)

    logger.info("=== Test Complete ===")
    logger.info("\nMessages processed. Society is operational!")

    # Phase 2: LLM-assisted dry-run decision (requires local gateway)
    phase2_mode = os.environ.get("PHASE2_DEV") == "1"
    if phase2_mode:
        logger.info("\n=== Phase 2: LLM-Assisted Planner Decision (Dry-Run) ===")
        try:
            # Reuse the previously built context, or build from last message (may be None)
            if not phase1_mode:
                planner_context = planner_agent.build_llm_context(user_message)
            decision = await planner_agent.reason_with_llm(planner_context)
            # For dev UX also send a notification to InterfaceAgent so it prints to console
            await message_bus.publish(
                Message(
                    message_type=MessageType.NOTIFICATION,
                    sender_id=planner_agent.agent_id,
                    receiver_id="user",
                    content=(
                        "— LLM DECISION (Planner) —\n"
                        f"chosen_route: {decision['chosen_route']}\n"
                        f"confidence: {decision['confidence']:.2f}\n"
                        f"needs_user_confirmation: {decision['needs_user_confirmation']}"
                    ),
                ),
                direct_dispatch=True,
            )
        except Exception as e:
            logger.error(f"Phase 2 LLM decision failed: {e}")

        # Demonstrate Gatekeeper advisory once with a mock request
        try:
            from actions.action_request import ActionRequest, ActionType, Reversibility, DataSensitivity

            mock_req = ActionRequest(
                requester_agent_id="PlannerAgent_main_v1",
                requester_role="PlannerAgent",
                action_type=ActionType.NETWORK_UPLOAD,
                justification="Upload sample metadata to cloud",
                user_impact="May incur network usage",
                data_sensitivity=DataSensitivity.MEDIUM,
                estimated_cost_eur=0.0,
                estimated_runtime_sec=1.0,
                reversibility=Reversibility.SOFT_REVERSIBLE,
                requires_user_approval=False,
            )
            advisory = await gatekeeper_agent.advise_on(mock_req)
            await message_bus.publish(
                Message(
                    message_type=MessageType.NOTIFICATION,
                    sender_id=gatekeeper_agent.agent_id,
                    receiver_id="user",
                    content=(
                        "— LLM ADVISORY (Gatekeeper) —\n"
                        f"suggested_decision: {advisory.get('suggested_decision')}\n"
                        f"risk_summary: {advisory.get('risk_summary')}"
                    ),
                ),
                direct_dispatch=True,
            )
        except Exception as e:
            logger.error(f"Gatekeeper advisory failed: {e}")

    async def interactive_chat() -> None:
        print("\nEntering interactive mode. Type 'exit' to quit.\n")
        try:
            while True:
                try:
                    # Read line without blocking the event loop
                    line = await asyncio.to_thread(input, "[You] ")
                except EOFError:
                    break
                if line is None:
                    continue
                line = line.strip()
                if line.lower() in {"exit", "quit", ":q", "\":q\""}:
                    break
                if not line:
                    continue

                msg = Message(
                    message_type=MessageType.REQUEST,
                    sender_id="user",
                    content=line,
                )
                await interface_agent.handle(msg)
                # allow handlers to process
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            pass

    if interactive_mode:
        await interactive_chat()
    else:
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            # Stop message bus
            message_bus.stop()
            logger.info("MVS shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
