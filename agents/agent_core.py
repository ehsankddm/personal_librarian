"""Agent core - Base class for all agents conforming to AGENT.md specification."""

from abc import ABC, abstractmethod
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, Optional

from asyncio.log import logging  # noqa: UP035

from actions.action_request import ActionRequest
from core.message import Message, MessageType, Telemetry
from memory.recall import Recall


class Agent(ABC):
    """
    Base class for all agents in the society.

    This class implements the full skeleton specification from AGENT.md.
    All agents in the Personal Librarian system must inherit from this.
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        name: str,
        traits: Dict[str, Any] = None,
        replica_id: Optional[str] = None,
        registry=None,
        message_bus=None,
        preferences=None,
        policies=None,
        telemetry_collector=None,
        memory_log=None,
        gatekeeper=None,
        instincts_path: Optional[str] = None,
        logger=None,
        **kwargs,
    ):
        """
        Initialize an agent.

        Args:
            agent_id: Unique identifier for this agent instance
            role: Agent's role (e.g., "Planner", "Gatekeeper", "BackupAgent")
            name: Human-readable name
            traits: Dict encoding variant behavior for routing/learning
            replica_id: Optional replica identifier
            registry: Agent registry for tracking
            message_bus: Message bus for communication
            preferences: Preference manager
            policies: Policy manager
            telemetry_collector: Telemetry collector for logging
            memory_log: Memory logger for diaries
            gatekeeper: Gatekeeper for action approval
            instincts_path: Path to instinct markdown file
        """
        # Required metadata (Section 2)
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.traits = traits or {}
        self.replica_id = replica_id

        # System references
        self.registry = registry
        self.message_bus = message_bus
        self.preferences = preferences
        self.policies = policies
        self.telemetry_collector = telemetry_collector
        self.memory_log = memory_log
        self.gatekeeper = gatekeeper

        # Load instincts (Section 2)
        self.instinct_paths = self._load_instinct_paths()
        self.instinct_text = self._load_instincts()

        # Memory path (Section 2)
        self.memory_path = Path(f"memory/agents/{agent_id}")
        self.memory_path.mkdir(parents=True, exist_ok=True)

        # State
        self.retired = False
        self.retry_count = 0
        self.max_retries = 3  # Default, can be overridden by preferences

        # Note: Agents must self-register via describe_capabilities() after initialization
        # because Registry.register_agent requires capabilities_summary

        # Initialize Recall for memory retrieval
        if memory_log:
            self.recall = Recall(memory_log)
        else:
            self.recall = None

        self.logger = logger or logging.getLogger(__name__)  # noqa: UP006

    def _load_instinct_paths(self) -> list[str]:
        """Load instinct file paths (society_values + default + role-specific)."""
        paths = []

        # Always load society_values first
        if Path("instincts/society_values.md").exists():
            paths.append("instincts/society_values.md")

        # Add default agent instinct
        if Path("instincts/default_agent_instinct.md").exists():
            paths.append("instincts/default_agent_instinct.md")

        # Add role-specific instinct
        # Try full role name first, then without "Agent" suffix
        role_instinct = f"instincts/{self.role.lower()}_instinct.md"
        if Path(role_instinct).exists():
            paths.append(role_instinct)
        else:
            # Try without "Agent" suffix (e.g. "PlannerAgent" -> "planner")
            role_without_agent = self.role.lower().replace("agent", "")
            role_instinct_alt = f"instincts/{role_without_agent}_instinct.md"
            if Path(role_instinct_alt).exists():
                paths.append(role_instinct_alt)

        return paths

    def _load_instincts(self) -> str:
        """Load and combine all instinct files."""
        instincts = []
        for path in self.instinct_paths:
            try:
                with open(path, "r") as f:
                    instincts.append(f.read())
            except FileNotFoundError:
                pass
        return "\n\n---\n\n".join(instincts)

    # === Abstract Methods (must be implemented by subclasses) ===

    @abstractmethod
    async def can_handle(self, message: Message) -> bool:
        """
        Determine if this agent can handle the message.

        Args:
            message: The message to evaluate

        Returns:
            True if this agent should handle the message

        Section 3.1: Must be honest about capability.
        """
        pass

    @abstractmethod
    async def handle(self, message: Message) -> Optional[Message]:
        """
        Handle a message.

        Args:
            message: The message to handle

        Returns:
            Response message or None

        Section 3.2: Must acknowledge, describe intent, execute,
        emit telemetry, escalate if blocked.
        """
        pass

    @abstractmethod
    def describe_capabilities(self) -> str:
        """
        Return a short English description of what this agent can do.

        Section 10.1: Used by Planner, Curator, CodeGenerator for routing.

        Returns:
            English description of capabilities
        """
        pass

    # === Communication Methods (Section 3) ===

    async def speak(
        self,
        content: str,
        recipient: str = "Planner",
        message_type: MessageType = MessageType.NOTIFICATION,
        tags: Optional[list[str]] = None,
    ):
        """
        Helper method to create and publish a message.

        Section 3.3: Always speaks in English, not logs.

        Args:
            content: Message content in English
            recipient: Target agent ID or "User"
            message_type: Type of message
            tags: Optional tags for routing
        """
        if not self.message_bus or self.retired:
            return

        message = Message(
            message_type=message_type,
            sender_id=self.agent_id,
            content=content,
            receiver_id=recipient,
            tags=tags or [],
        )
        await self.message_bus.publish(message)

    # === Safety & Gatekeeper (Section 4) ===

    async def propose_action(self, request: ActionRequest):
        """
        Propose an action to the Gatekeeper.

        Section 4.1: All risky operations must go through Gatekeeper.

        Args:
            request: Action request with details
        """
        if not self.gatekeeper:
            raise RuntimeError("No gatekeeper available")

        # Gatekeeper will evaluate and either approve, deny, or escalate
        await self.gatekeeper.evaluate_action(request)

    # === Telemetry (Section 5) ===

    def log_event(self, event_dict: Dict[str, Any]):
        """
        Log an event for learning.

        Section 5.1: Must log at minimum:
        - type: "task_result" | "escalation" | "message_exchange"
        - agent_id, role

        Args:
            event_dict: Event data
        """
        if not self.telemetry_collector:
            return

        # Add required fields
        event_dict["agent_id"] = self.agent_id
        event_dict["role"] = self.role

        # Create telemetry and collect
        telemetry = Telemetry(
            agent_id=self.agent_id,
            action=event_dict.get("type", "unknown"),
            success=event_dict.get("success", False),
            cost=event_dict.get("cost", 0.0),
            duration_ms=event_dict.get("duration_ms", 0.0),
            metadata=event_dict,
        )

        self.telemetry_collector.collect(telemetry)

    # === Escalation (Section 7) ===

    async def escalate(self, what_tried: str, why_blocked: str, options: list[str], question: str):
        """
        Escalate when stuck or blocked.

        Section 7.2: Must send English message with:
        - What I tried
        - Why I'm blocked
        - Options
        - Direct question

        Args:
            what_tried: Description of what was attempted
            why_blocked: Reason for being blocked
            options: List of possible options
            question: Direct question to user
        """
        content = f"""I'm {self.agent_id}.

I tried: {what_tried}

Why I'm blocked: {why_blocked}

Options:
{chr(10).join(f"- {opt}" for opt in options)}

{question}"""

        await self.speak(
            content=content,
            recipient="Planner",
            message_type=MessageType.ESCALATION,
            tags=["escalation", self.role],
        )

        # Log escalation
        self.log_event(
            {
                "type": "escalation",
                "what_tried": what_tried,
                "why_blocked": why_blocked,
                "options": options,
                "success": False,
            }
        )

    # === Memory (Section 8) ===

    def log_memory_entry(self, entry: str, timestamp: Optional[datetime] = None):
        """
        Append an entry to agent's memory diary.

        Section 8: Must log completed tasks, escalations, policy conflicts,
        lessons learned, user feedback.

        Args:
            entry: Memory entry text
            timestamp: Optional timestamp (uses now if not provided)
        """
        if self.memory_log:
            self.memory_log.log_entry(
                agent_id=self.agent_id, entry=entry, timestamp=timestamp or datetime.now(UTC)
            )

    # === Lifecycle (Section 10) ===

    def retire(self, reason: str):
        """
        Retire this agent replica.

        Section 10.2: Write final memory, mark inactive, stop responding.

        Args:
            reason: Reason for retirement
        """
        # Write final memory entry
        self.log_memory_entry(
            f"# Retirement Notice\n\nReason: {reason}\n\nRetired at: {datetime.now(UTC).isoformat()}"
        )

        # Mark as retired
        self.retired = True

        # Update registry status
        if self.registry:
            agent_info = self.registry.get_agent(self.agent_id)
            if agent_info:
                agent_info.status = "retired"

        # Log event
        self.log_event({"type": "retirement", "reason": reason, "success": False})

    # === Helper Methods ===

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        if not self.preferences:
            return default
        return self.preferences.get(key, default)

    def check_policy(self, action_type: str) -> tuple[bool, Dict[str, Any]]:
        """Check if an action is allowed by policy."""
        if not self.policies:
            return False, {}
        return self.policies.check(action_type)

    def should_escalate(self) -> bool:
        """Check if agent should escalate based on retry count."""
        return self.retry_count >= self.max_retries

    def __repr__(self) -> str:
        return f"Agent(agent_id={self.agent_id}, role={self.role}, retired={self.retired})"

    # === Phase 1: LLM Context Bundling ===

    def build_llm_context(self, incoming_message: Optional[Message] = None) -> Dict[str, Any]:
        """
        Build LLM context bundle for this agent.

        Per PHASE_1_ROADMAP §1: Packages identity, instincts, policies, preferences,
        recent memory, and task context for LLM reasoning.

        This will be sent to a model in Phase 2 for decision-making.

        Args:
            incoming_message: Optional current message being processed

        Returns:
            Dictionary containing structured reasoning context
        """
        # Get recent memory snippets
        recent_memory = []
        if self.recall:
            recent_memory = self.recall.recall_recent_memory(self.agent_id, max_items=5)

        # Get preferences and policies snapshots
        prefs_snapshot = {}
        if self.preferences:
            # Get relevant preferences for this agent
            prefs_snapshot = {
                "verbosity": self.preferences.get("communication.verbosity", "normal"),
                "style": self.preferences.get("communication.style", "neutral"),
                "summary_style": self.preferences.get("summary.style", "short_bullets"),
                "max_retries": self.preferences.get("max_retries", 3),
            }

        policies_snapshot = {}
        if self.policies:
            # Get relevant policy constraints
            policies_snapshot = {
                "network_allowed": self.policies.get("network.allow_external_requests", False),
                "cost_limit": self.policies.get("cost.max_cloud_cost_per_day_eur", 0),
                "filesystem_write": self.policies.get("filesystem.allow_delete", False),
            }

        # Extract incoming message info
        incoming_info = {}
        if incoming_message:
            incoming_info = {
                "sender": incoming_message.sender_id,
                "content": incoming_message.content,
                "tags": incoming_message.tags or [],
            }

        return {
            "agent_identity": {"role": self.role, "agent_id": self.agent_id, "traits": self.traits},
            "instincts": self.instinct_text,
            "policies": policies_snapshot,
            "preferences": prefs_snapshot,
            "recent_memory": recent_memory,
            "incoming_message": incoming_info,
            "task_hypothesis": self._build_task_hypothesis(incoming_message),
            "candidate_actions": self._build_candidate_actions(incoming_message),
            "escalation_policy": self._build_escalation_policy(),
            "questions_for_reasoner": self._build_questions(incoming_message),
        }

    def _build_task_hypothesis(self, message: Optional[Message]) -> str:
        """Build hypothesis about what the task is."""
        if not message:
            return "No current task."
        return f"Processing message from {message.sender_id}: {message.content[:100]}"

    def _build_candidate_actions(self, message: Optional[Message]) -> list[str]:
        """Build list of candidate actions."""
        return ["Analyze request", "Escalate if needed", "Log results"]

    def _build_escalation_policy(self) -> str:
        """Build escalation rules."""
        max_retries = self.preferences.get("max_retries", 3) if self.preferences else 3
        return f"Escalate to Planner or User after {max_retries} attempts, or if blocked by policy, or if irreversible/high-cost action required."

    def _build_questions(self, message: Optional[Message]) -> list[str]:
        """Build questions for the reasoner."""
        return ["What is the best approach for this task?", "Should I escalate or proceed?"]
