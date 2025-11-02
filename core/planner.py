"""Planner - Central coordinator and router per PLANNER.md specification."""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import uuid

from core.message import Message, MessageType, Task, TaskStatus
from core.registry import Registry, AgentInfo
from learning.router_learner import RouterLearner
from memory.society_memory import SocietyMemory


@dataclass
class TaskIntent:
    """Parsed task intent from a message."""

    task_type: str
    goal: str
    entities: list[str]
    urgency: str = "normal"
    context: str = "unknown"
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class Planner:
    """
    Central coordinator and router per PLANNER.md.

    Ensures every request finds the right executor - safely, efficiently,
    and in line with learned preferences and policies.
    """

    def __init__(
        self,
        registry: Registry,
        message_bus,
        router_learner: RouterLearner,
        society_memory: SocietyMemory,
        telemetry_collector=None,
    ):
        self.registry = registry
        self.message_bus = message_bus
        self.router_learner = router_learner
        self.society_memory = society_memory
        self.telemetry_collector = telemetry_collector

        self.active_tasks: dict[str, Task] = {}
        self.routing_history: list[Dict[str, Any]] = []
        self.tasks_completed_today = 0
        self.tasks_failed_today = 0

    # === Core Workflow Methods ===

    async def receive_message(self, message: Message) -> Optional[Message]:
        """
        Entry point for new message or user request.
        Per PLANNER.md Section 5.1
        """
        # Interpret intent
        intent = await self.interpret_intent(message)

        # Find candidates
        candidates = await self.find_candidates(intent)

        if not candidates:
            # No candidates - handle missing capability
            return await self.handle_missing_capability(intent, message)

        # Filter by policy
        filtered = await self.filter_by_policy_and_scope(candidates, intent)

        if not filtered:
            # No valid candidates after policy filtering
            return await self.escalate_to_user(
                "No agents available due to policy constraints", message
            )

        # Rank candidates
        ranked = await self.rank_candidates(filtered, intent)

        if not ranked:
            # No ranked candidates
            return await self.escalate_to_user(
                "Could not determine best agent for this task", message
            )

        # Route to best
        best_candidate = ranked[0]
        result = await self.route_to_best(intent, best_candidate, message)

        # Monitor progress and reward feedback handled by message handlers

        return result

    async def interpret_intent(self, message: Message) -> TaskIntent:
        """
        Parse message content into structured task intent.
        Per PLANNER.md Section 5.2(1)
        """
        content = message.content.lower()

        # Simple rule-based parsing (TODO: LLM-based for Phase 1)
        task_type = "unknown"
        goal = message.content
        entities = []
        tags = message.tags.copy() if message.tags else []

        # Keyword-based intent detection
        if any(word in content for word in ["import", "ingest", "scan"]):
            task_type = "ingestion"
            tags.extend(["ingestion", "new_books"])

        elif any(word in content for word in ["backup", "upload", "sync"]):
            task_type = "backup"
            tags.extend(["backup", "upload"])

        elif any(word in content for word in ["metadata", "enrich", "tag"]):
            task_type = "enrichment"
            tags.extend(["metadata", "enrichment"])

        elif any(word in content for word in ["generate", "create", "spawn"]):
            task_type = "agent_creation"
            tags.extend(["agent_creation"])

        # Detect urgency
        urgency = "normal"
        if any(word in content for word in ["urgent", "asap", "immediately"]):
            urgency = "high"

        # Detect context
        context = "user_request" if message.sender_id == "user" else "agent_request"

        return TaskIntent(
            task_type=task_type,
            goal=goal,
            entities=entities,
            urgency=urgency,
            context=context,
            tags=tags,
        )

    async def find_candidates(self, intent: TaskIntent) -> List[AgentInfo]:
        """
        Query registry for active replicas with relevant capabilities.
        Per PLANNER.md Section 5.2(2)
        """
        # Map task types to roles
        task_to_role = {
            "ingestion": "IngestionAgent",
            "backup": "BackupAgent",
            "enrichment": "EnrichmentAgent",
            "metadata": "WebMetadataAgent",
            "agent_creation": "CodeGeneratorAgent",
        }

        # Determine role to search for
        role = None
        if intent.task_type in task_to_role:
            role = task_to_role[intent.task_type]
        elif intent.task_type != "unknown":
            # Try to match by name
            role = intent.task_type.replace("_", "").title()

        # Use Registry's list_candidates for proper filtering
        candidates = self.registry.list_candidates(role=role)

        return candidates

    async def filter_by_policy_and_scope(
        self, candidates: List[AgentInfo], intent: TaskIntent
    ) -> List[AgentInfo]:
        """
        Use policies and preferences to prune candidates.
        Per PLANNER.md Section 5.2(3)
        """
        # TODO: Implement full policy filtering
        # For Phase 0, just return candidates
        return candidates

    async def rank_candidates(
        self, candidates: List[AgentInfo], intent: TaskIntent
    ) -> List[AgentInfo]:
        """
        Consult RouterLearner to pick best replica.
        Per PLANNER.md Section 5.2(4)
        """
        if not candidates:
            return []

        # Use RouterLearner to recommend agent
        recommended_id = self.router_learner.recommend_agent(intent.goal)

        if recommended_id:
            # Check if recommended agent is in candidates
            recommended = next((c for c in candidates if c.agent_id == recommended_id), None)
            if recommended:
                return [recommended] + [c for c in candidates if c.agent_id != recommended_id]

        # Otherwise, use registry's best_replica logic
        # Group by role
        by_role: Dict[str, List[AgentInfo]] = {}
        for candidate in candidates:
            if candidate.role not in by_role:
                by_role[candidate.role] = []
            by_role[candidate.role].append(candidate)

        # Rank by role first, then by performance
        ranked = []
        for role, role_candidates in by_role.items():
            best = self.registry.get_best_replica(role)
            if best:
                best_info = next((c for c in role_candidates if c.agent_id == best), None)
                if best_info:
                    ranked.append(best_info)
            # Add remaining candidates
            for candidate in role_candidates:
                if candidate.agent_id not in [r.agent_id for r in ranked]:
                    ranked.append(candidate)

        return ranked

    async def route_to_best(
        self, intent: TaskIntent, agent_info: AgentInfo, original_message: Message
    ) -> Optional[Message]:
        """
        Send message to selected replica via MessageBus.
        Per PLANNER.md Section 5.2(5)
        """
        # Create task
        task = await self.create_task(
            description=intent.goal, metadata={"intent": intent.task_type}
        )

        # Assign to agent
        await self.assign_task(task.task_id, agent_info.agent_id)

        # Forward message to agent
        route_message = Message(
            message_type=MessageType.REQUEST,
            sender_id="Planner",
            content=original_message.content,
            receiver_id=agent_info.agent_id,
            task_id=task.task_id,
            tags=intent.tags,
        )

        await self.message_bus.publish(route_message)

        # Log telemetry
        self.log_routing_decision(
            intent=intent.task_type,
            chosen_agent=agent_info.agent_id,
            alternatives_considered=len([agent_info]),
        )

        # Record in RouterLearner
        self.router_learner.record_routing(
            message_content=original_message.content,
            target_agent=agent_info.agent_id,
            success=True,  # Will be updated when result comes back
        )

        # Response to sender
        return Message(
            message_type=MessageType.RESPONSE,
            sender_id="Planner",
            content=f"Routed to {agent_info.agent_id}. Task {task.task_id}.",
            receiver_id=original_message.sender_id,
        )

    async def monitor_progress(self, message: Message):
        """
        Watch for progress, completion, escalation messages.
        Per PLANNER.md Section 5.2(6)
        """
        # Check for completion/escalation tags
        if "complete" in message.tags:
            await self.reward_feedback(message, success=True)
        elif "escalation" in message.tags:
            await self.handle_escalation(message)
        elif "failed" in message.tags:
            await self.reward_feedback(message, success=False)

    async def reward_feedback(self, message: Message, success: bool):
        """
        Log success/failure and update performance.
        Per PLANNER.md Section 5.2(7)
        """
        # Record in RouterLearner with actual outcome
        if message.task_id and message.task_id in self.active_tasks:
            task = self.active_tasks[message.task_id]
            if task.assigned_to:
                self.router_learner.record_routing(
                    message_content="",  # Don't have original content here
                    target_agent=task.assigned_to,
                    success=success,
                )

        # Log telemetry
        if self.telemetry_collector:
            from core.message import Telemetry

            telemetry = Telemetry(
                agent_id="Planner",
                action="routing",
                success=success,
                cost=0.0,
                duration_ms=0.0,
                metadata={"task_id": message.task_id},
            )
            self.telemetry_collector.collect(telemetry)

        # Track daily stats
        if success:
            self.tasks_completed_today += 1
            await self.complete_task(message.task_id, True)
        else:
            self.tasks_failed_today += 1
            await self.complete_task(message.task_id, False)

    # === Missing Capability Handling ===

    async def handle_missing_capability(
        self, intent: TaskIntent, original_message: Message
    ) -> Optional[Message]:
        """
        Handle missing capabilities by requesting agent creation.
        Per PLANNER.md Section 6
        """
        # Draft capability spec
        spec_content = f"""
# Capability Request

## Need
{intent.goal}

## Task Type
{intent.task_type}

## Context
{intent.context}

## Required Capabilities
- {intent.task_type}

## Urgency
{intent.urgency}
        """

        # Write to requested_capabilities
        spec_id = str(uuid.uuid4())
        spec_path = Path(f"agents_generated_specs/requested_capabilities/{spec_id}.md")
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(spec_content)

        # Send to CodeGeneratorAgent
        generation_message = Message(
            message_type=MessageType.REQUEST,
            sender_id="Planner",
            content=f"Please create an agent for: {intent.goal}. Spec at {spec_path}",
            receiver_id="CodeGeneratorAgent",
            tags=["agent_creation", "missing_capability"],
        )

        await self.message_bus.publish(generation_message)

        # Log to society memory
        self.society_memory.add_entry(
            f"Missing capability detected for '{intent.task_type}'. "
            f"Requested CodeGeneratorAgent to create new agent."
        )

        # Response to user
        return Message(
            message_type=MessageType.RESPONSE,
            sender_id="Planner",
            content=f"I need to create a new agent for this task. Creating now...",
            receiver_id=original_message.sender_id,
        )

    # === Escalation Methods ===

    async def handle_escalation(self, message: Message):
        """
        Respond to blocked or failed tasks.
        Per PLANNER.md Section 7
        """
        if "missing capability" in message.content.lower():
            # Already handled by handle_missing_capability
            pass
        elif "blocked by policy" in message.content.lower():
            await self.escalate_to_user(f"Policy block: {message.content}", message)
        else:
            # Generic error - notify Curator
            await self.escalate_to_curator(f"Task error: {message.content}", message)

    async def escalate_to_user(self, reason: str, original_message: Message) -> Optional[Message]:
        """Escalate to user for decision."""
        escalation = Message(
            message_type=MessageType.ESCALATION,
            sender_id="Planner",
            content=f"Planner escalation: {reason}",
            receiver_id="user",
            tags=["escalation", "user_approval"],
        )

        await self.message_bus.publish(escalation)

        return Message(
            message_type=MessageType.RESPONSE,
            sender_id="Planner",
            content="Escalated to user for decision.",
            receiver_id=original_message.sender_id,
        )

    async def escalate_to_curator(self, reason: str, original_message: Message):
        """Escalate to CuratorAgent for learning."""
        escalation = Message(
            message_type=MessageType.ESCALATION,
            sender_id="Planner",
            content=f"Planner escalation: {reason}",
            receiver_id="CuratorAgent",
            tags=["escalation", "learning"],
        )

        await self.message_bus.publish(escalation)

        # Log to society memory
        self.society_memory.add_entry(f"Escalated to Curator: {reason}")

    # === Task Management ===

    async def create_task(self, description: str, metadata: dict = None) -> Task:
        """Create a new task."""
        task_id = f"task_{datetime.now().isoformat()}"
        task = Task(
            task_id=task_id,
            description=description,
            status=TaskStatus.PENDING,
            metadata=metadata or {},
        )
        self.active_tasks[task_id] = task
        return task

    async def assign_task(self, task_id: str, agent_id: str):
        """Assign a task to an agent."""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].assigned_to = agent_id
            self.active_tasks[task_id].status = TaskStatus.IN_PROGRESS

    async def complete_task(self, task_id: str, success: bool):
        """Mark a task as complete."""
        if task_id in self.active_tasks:
            status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            self.active_tasks[task_id].status = status

    # === Telemetry and Reflection ===

    def log_routing_decision(self, intent: str, chosen_agent: str, alternatives_considered: int):
        """Log routing decision for telemetry."""
        decision = {
            "intent": intent,
            "chosen_agent": chosen_agent,
            "alternatives_considered": alternatives_considered,
            "timestamp": datetime.now().isoformat(),
        }
        self.routing_history.append(decision)

    async def summarize_day(self):
        """
        Write daily summary to society memory.
        Per PLANNER.md Section 8.3
        """
        summary = f"""
## Daily Summary

### Tasks
- Tasks completed: {self.tasks_completed_today}
- Tasks failed: {self.tasks_failed_today}
- Total routes: {len(self.routing_history)}

### Agents
- Active agents: {len(self.registry.get_agents())}
- Routes made: {len([r for r in self.routing_history])}

### Performance
- Success rate: {self.tasks_completed_today / max(self.tasks_completed_today + self.tasks_failed_today, 1):.2%}
        """

        self.society_memory.add_entry(summary)

        # Reset counters for next day
        self.tasks_completed_today = 0
        self.tasks_failed_today = 0

    def __repr__(self) -> str:
        return f"Planner(active_tasks={len(self.active_tasks)}, routes={len(self.routing_history)})"
