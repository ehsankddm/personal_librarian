"""Planner Agent - Coordinates and routes tasks per PLANNER.md."""

import datetime
import os
from typing import Any, Dict, List, Optional

from agents.agent_core import Agent
from core.message import Message, MessageType


class PlannerAgent(Agent):
    """
    Agent responsible for coordination and task routing.

    This is the wrapper agent that uses the core Planner logic.
    """

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    async def can_handle(self, message: Message) -> bool:
        """
        Handle coordination and routing messages.
        Per PLANNER.md Section 1: The Planner is the central coordinator.
        """
        if self.retired:
            return False

        # Handle requests and escalations
        # Also handle specific routing keywords
        return (
            message.message_type in [MessageType.REQUEST, MessageType.ESCALATION]
            or message.receiver_id == "Planner"
            or message.receiver_id == self.agent_id
            or "route" in message.content.lower()
            or "coordinate" in message.content.lower()
        )

    async def handle(self, message):
        """
        Your existing message handler probably:
        - interprets user intent,
        - maybe routes or asks CodeGeneratorAgent,
        - and responds to InterfaceAgent.

        We will KEEP that behavior.
        At the end (only in PHASE1_DEV), we will also dump reasoning bundles.
        """
        # ---- existing logic start (don't remove yours) ----
        # assume message.content is user request text
        user_text = getattr(message, "content", "")
        self.logger.info(f"User request: {user_text}")  # noqa: UP006
        plan = await self.plan_next_step(message)
        self.logger.info(f"Plan: {plan}")  # noqa: UP006

        # send the normal human-facing reply (Phase 0 behavior)
        if plan.get("explanation_for_user"):
            await self.speak(
                content=plan["explanation_for_user"],
                recipient="InterfaceAgent_main_v1",
                message_type=MessageType.NOTIFICATION,
            )
            self.logger.info(f"Explanation for user: {plan['explanation_for_user']}")  # noqa: UP006
        self.logger.info(f"PHASE1_DEV: {os.environ.get('PHASE1_DEV')}")
        if os.environ.get("PHASE1_DEV") == "1":
            llm_ctx = self.build_llm_context(message, plan)
            self._print_llm_bundle(llm_ctx, plan)

    def _print_llm_bundle(self, llm_ctx: Dict[str, Any], plan: Dict[str, Any]) -> None:  # noqa: UP006
        """
        Developer-facing dump. This should look like the Phase 1 expected transcript.
        We DO NOT send this over the bus. Just local stdout/log.
        """
        # You likely already have self.logger on AgentCore; if not, import `logging` and use logging.getLogger(__name__)
        self.logger.info("\n--- LLM CONTEXT (%s) ---", self.agent_id)
        self.logger.info("agent_identity.role: %s", llm_ctx["agent_identity"]["role"])
        self.logger.info("agent_identity.agent_id: %s", llm_ctx["agent_identity"]["agent_id"])
        self.logger.info("task_hypothesis: %s", llm_ctx.get("task_hypothesis"))
        self.logger.info("candidate_actions:")
        for act in llm_ctx.get("candidate_actions", []):
            self.logger.info(" - %s", act)
        self.logger.info("policy_blocks:")
        for pb in plan.get("policy_blocks", []):
            self.logger.info(" - %s", pb)
        self.logger.info("escalation_policy: %s", llm_ctx.get("escalation_policy"))
        self.logger.info("questions_for_reasoner:")
        for q in llm_ctx.get("questions_for_reasoner", []):
            self.logger.info(" - %s", q)

        self.logger.info("\n--- ROUTING PLAN (%s) ---", self.agent_id)
        self.logger.info("intent_guess: %s", plan.get("intent_guess"))
        self.logger.info("candidate_agents: %s", plan.get("candidate_agents"))
        self.logger.info("proposed_route: %s", plan.get("proposed_route"))
        self.logger.info("explanation_for_user: %s", plan.get("explanation_for_user"))
        self.logger.info("")

    def build_llm_context(
        self,
        incoming_message,
        plan: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Phase 1 requirement:
        Package identity, instincts, policy, memory, and next-step intent
        so an LLM could reason about what Planner should do next.

        We DO NOT CALL THE LLM HERE. We only assemble context for inspection/logging.
        """

        # Message info
        msg_sender = getattr(incoming_message, "sender", "unknown")
        msg_content = getattr(incoming_message, "content", "")
        msg_tags = getattr(incoming_message, "tags", [])

        # Pull a short memory window. This can be crude in Phase 1.
        recent_memory_snippets = self._recall_recent_memory_snippets(max_items=5)

        # candidate next actions (human text) for planner to consider
        candidate_actions: List[str] = []
        if plan and plan.get("proposed_route"):
            candidate_actions.append(plan["proposed_route"])
        # we can also add safe fallbacks
        candidate_actions.append("Ask user for clarification if path or scope is ambiguous.")
        candidate_actions.append("Escalate to CodeGeneratorAgent to generate missing capability.")
        candidate_actions.append("Do nothing further and wait for approval.")

        # escalation policy summary (static for Phase 1)
        escalation_policy = (
            "If no capable agent exists, propose agent creation via CodeGeneratorAgent. "
            "If action would touch filesystem, network, spend money, or expose private data, "
            "ask Gatekeeper and/or the user before proceeding."
        )

        # what do we *think* the user wants? (best guess heuristic)
        task_hypothesis = self._infer_task_hypothesis(msg_content)

        # what questions would we ask an LLM if we had one?
        questions_for_reasoner = [
            "Is creating a new ingestion agent the correct next step?",
            "Should I ask the user for a path/device hint before generating an agent?",
            "Is any policy blocking this route right now?",
        ]

        ctx = {
            "agent_identity": {
                "role": getattr(self, "role", "Planner"),
                "agent_id": getattr(self, "agent_id", ""),
                "traits": getattr(self, "traits", {}),
            },
            "instincts": getattr(self, "instinct_text", ""),
            "policies": getattr(self, "policies", {}),
            "preferences": getattr(self, "preferences", {}),
            "recent_memory": recent_memory_snippets,
            "incoming_message": {
                "sender": msg_sender,
                "content": msg_content,
                "tags": msg_tags,
                "received_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
            },
            "task_hypothesis": task_hypothesis,
            "candidate_actions": candidate_actions,
            "escalation_policy": escalation_policy,
            "questions_for_reasoner": questions_for_reasoner,
        }

        return ctx

    async def plan_next_step(self, incoming_message) -> Dict[str, Any]:
        """
        Phase 1 requirement:
        Produce a routing reasoning bundle:
        - what's the intent,
        - what agents/replicas could handle it,
        - what policy blocks exist,
        - what we plan to do.

        This is still deterministic. We are NOT calling an LLM.
        """

        user_text = getattr(incoming_message, "content", "")

        # Intent guess (very dumb heuristic for Phase 1)
        if "import" in user_text.lower() and "book" in user_text.lower():
            intent_guess = "ingest_books"
        else:
            intent_guess = "unknown"

        # Ask Registry who might handle this capability
        # We assume self.registry.list_candidates(role="IngestionAgent") or similar is available.
        # If registry doesn't have this role, we treat it as missing.
        candidate_ingestors = []
        if hasattr(self, "registry") and hasattr(self.registry, "list_candidates"):
            try:
                candidate_ingestors = self.registry.list_candidates(role="IngestionAgent")
            except Exception:
                candidate_ingestors = []

        candidate_agent_ids = (
            [c.get("agent_id") for c in candidate_ingestors] if candidate_ingestors else []
        )

        # Policy blocks: we know ingestion isn't implemented yet in Phase 1
        policy_blocks = []
        if not candidate_agent_ids:
            policy_blocks.append(
                "No ingestion agent registered yet (cannot directly read Android downloads)."
            )

        # Proposed route:
        # If we have no ingestion agent, we request CodeGeneratorAgent to generate one.
        if not candidate_agent_ids:
            proposed_route = "Request CodeGeneratorAgent to create a new IngestionAgent for Android download scanning."
            explanation_for_user = (
                "I currently do not have an IngestionAgent that can safely scan your Android downloads. "
                "I'll request a new ingestion capability. No files were moved."
            )
        else:
            proposed_route = f"Assign ingestion task to {candidate_agent_ids[0]}"
            explanation_for_user = (
                f"I will ask {candidate_agent_ids[0]} to ingest new books safely. "
                "No files were moved yet."
            )

        plan = {
            "intent_guess": intent_guess,
            "candidate_agents": candidate_agent_ids,
            "policy_blocks": policy_blocks,
            "proposed_route": proposed_route,
            "explanation_for_user": explanation_for_user,
        }

        return plan

    def _recall_recent_memory_snippets(self, max_items: int = 5) -> List[str]:
        """
        Phase 1 helper.
        Pulls recent memory lines for this agent or from society memory.
        For now it's okay to stub graceful behavior.
        """
        # If you already have memory.recall.recall_recent_memory(), call it here.
        # Otherwise, return a bounded stub.
        snippets = [
            "[2025-11-01T16:59Z] Planner routed a request to CodeGeneratorAgent for ingestion capability.",
            "[2025-11-01T16:58Z] No ingestion agent available; user asked to import Android books.",
        ]
        return snippets[:max_items]

    def _infer_task_hypothesis(self, text: str) -> str:
        """
        Extremely dumb intent guesser for Phase 1.
        """
        lower = text.lower()
        if "import" in lower and "book" in lower:
            return "User wants to import new books from their Android downloads folder into the library."
        if "backup" in lower:
            return "User wants to back up content safely."
        return "User is asking for library operations."

    def describe_capabilities(self) -> str:
        """
        Return a short human-readable summary of what this agent claims it can do.
        This satisfies AgentCore's abstract interface.
        Phase 1: this is static / hand-written.
        """
        return (
            "I am the Planner. I interpret user requests, break them into steps, "
            "check which agents or replicas can handle each step, respect policy "
            "and safety limits, and decide what should happen next. "
            "If no existing agent can do the task, I request that a new agent be "
            "created (for example, via CodeGeneratorAgent). I do not directly "
            "execute filesystem or network actions; those must go through Gatekeeper."
        )
