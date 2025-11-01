#!/usr/bin/env python3
"""
Development entry point for Personal Librarian.
Starts the minimal viable society (MVS) per Phase 0.
"""

import asyncio
import logging
from pathlib import Path

# Core imports
from core.bus import MessageBus
from core.message import Message, MessageType
from core.registry import Registry
from core.planner import Planner
from core.gatekeeper import Gatekeeper
from core.policies import PolicyManager
from core.preferences import PreferenceManager
from actions.executor import ActionExecutor

# Learning and memory
from learning.router_learner import RouterLearner
from learning.telemetry_collector import TelemetryCollector
from memory.society_memory import SocietyMemory
from memory.memory_log import MemoryLog

# Agents
from agents.planner_agent import PlannerAgent
from agents.gatekeeper_agent import GatekeeperAgent
from agents.interface_agent import InterfaceAgent
from agents.curator_agent import CuratorAgent
from agents.code_generator_agent import CodeGeneratorAgent
from agents.reflection_agent import ReflectionAgent

# Configure logging
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/runtime.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Start the MVS."""
    logger.info("Starting Personal Librarian MVS (Phase 0)...")
    
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
    message_bus = MessageBus()
    registry = Registry()
    router_learner = RouterLearner(registry)
    society_memory = SocietyMemory()
    telemetry_collector = TelemetryCollector()
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
        telemetry_collector=telemetry_collector
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
        gatekeeper=gatekeeper
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
        memory_log=memory_log
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
        gatekeeper=gatekeeper
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
        gatekeeper=gatekeeper
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
        gatekeeper=gatekeeper
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
        gatekeeper=gatekeeper
    )
    
    logger.info("Registering agents with Registry...")
    
    # Register all agents
    agents = [
        planner_agent,
        gatekeeper_agent,
        interface_agent,
        curator_agent,
        code_generator_agent,
        reflection_agent
    ]
    
    for agent in agents:
        registry.register_agent(
            agent_id=agent.agent_id,
            role=agent.role,
            capabilities_summary=agent.describe_capabilities(),
            traits=agent.traits,
            instinct_paths=agent.instinct_paths,
            society_memory=society_memory
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
        logger.info(f"  - {agent.agent_id}: {len(agent.instinct_paths)} instinct files, "
                   f"{len(agent.instinct_text)} chars of behavior DNA")
    
    # Test: Simulate one user request to prove "society is alive"
    logger.info("\n=== Testing Society Communication ===")
    logger.info("Simulating user request: 'Import all new books from my Android downloads'")
    
    user_message = Message(
        message_type=MessageType.REQUEST,
        sender_id="user",
        content="Import all new books from my Android downloads",
        receiver_id=None
    )
    
    # Send through InterfaceAgent
    print("\n[User] Import all new books from my Android downloads\n")
    await interface_agent.handle(user_message)
    
    # Give agents time to process
    await asyncio.sleep(0.5)
    
    logger.info("=== Test Complete ===")
    logger.info("\nMessages processed. Society is operational!")
    
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
