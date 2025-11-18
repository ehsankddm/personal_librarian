"""Planner Agent - Coordinates and routes tasks per PLANNER.md."""

import datetime
import os
from typing import Any, Dict, List, Optional

from agents.agent_core import Agent
from core.message import Message, MessageType
from core.llm_client import LLMClient
import json
import re
from pathlib import Path
import json as _json
from actions.action_request import ActionRequest, ActionType, Reversibility, DataSensitivity
from core.loader import AgentLoader


class PlannerAgent(Agent):
    """
    Agent responsible for coordination and task routing.

    This is the wrapper agent that uses the core Planner logic.
    """

    def __init__(
        self,
        planner=None,
        **kwargs,
    ):
        # Store reference to core Planner for routing/handling
        self.planner = planner
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

        # Detect explicit user approval to load a generated scaffold
        if (
            isinstance(message.content, str)
            and message.sender_id == "user"
            and re.search(r"\bapprove\s+load\b", message.content.lower())
        ):
            # Extract manifest path if provided, else pick the latest
            m = re.search(r"(agents/dynamic/.+?/MANIFEST\.json)", message.content)
            manifest_path = None
            if m:
                manifest_path = m.group(1)
            else:
                # Find the most recent manifest
                candidates = list(Path("agents/dynamic").glob("*/MANIFEST.json"))
                if candidates:
                    manifest_path = str(max(candidates, key=lambda p: p.stat().st_mtime))

            if not manifest_path or not Path(manifest_path).exists():
                await self.speak(
                    content=(
                        "No scaffold manifest found. Please specify a manifest path, e.g.\n"
                        "approve load agents/dynamic/GeneratedAgent_v1/MANIFEST.json"
                    ),
                    recipient="user",
                    message_type=MessageType.NOTIFICATION,
                )
            else:
                await self._approve_and_load_scaffold(manifest_path)

            # Do not continue routing this approval message
            return

        # Detect explicit user request to activate a loaded (registered) agent
        if (
            isinstance(message.content, str)
            and message.sender_id == "user"
            and re.search(r"\bactivate\s+agent\b", message.content.lower())
        ):
            m = re.search(r"activate\s+agent\s+([A-Za-z0-9_]+)", message.content)
            if not m:
                await self.speak(
                    content=(
                        "Please specify the agent name to activate, e.g.\n"
                        "activate agent GeneratedAgent_v1"
                    ),
                    recipient="user",
                    message_type=MessageType.NOTIFICATION,
                )
            else:
                agent_name = m.group(1)
                await self._approve_and_activate_agent(agent_name)
            return

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

        # Route into core Planner only for actionable messages to avoid loops
        try:
            if message.message_type in {MessageType.REQUEST, MessageType.ESCALATION} and message.sender_id not in {
                self.agent_id,
                "CodeGeneratorAgent_main_v1",
            }:
                result = await self.planner.receive_message(message)
                if result:
                    # Forward Planner response to its intended receiver
                    await self.speak(
                        content=result.content,
                        recipient=result.receiver_id or "InterfaceAgent_main_v1",
                        message_type=result.message_type,
                        tags=result.tags,
                    )
        except Exception as e:
            self.logger.error(f"PlannerAgent forwarding to core Planner failed: {e}")  # noqa: UP006

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

        # Build snapshots for preferences and policies similar to Agent base implementation
        prefs_snapshot = {
            "verbosity": getattr(self.preferences, "get", lambda *a, **k: None)(
                "communication.verbosity", "normal"
            )
            if getattr(self, "preferences", None)
            else "normal",
            "style": getattr(self.preferences, "get", lambda *a, **k: None)(
                "communication.style", "neutral"
            )
            if getattr(self, "preferences", None)
            else "neutral",
            "summary_style": getattr(self.preferences, "get", lambda *a, **k: None)(
                "summary.style", "short_bullets"
            )
            if getattr(self, "preferences", None)
            else "short_bullets",
            "max_retries": getattr(self.preferences, "get", lambda *a, **k: None)(
                "max_retries", 3
            )
            if getattr(self, "preferences", None)
            else 3,
        }

        policies_snapshot = {
            "network_allowed": getattr(self.policies, "get", lambda *a, **k: None)(
                "network.allow_external_requests", False
            )
            if getattr(self, "policies", None)
            else False,
            "cost_limit": getattr(self.policies, "get", lambda *a, **k: None)(
                "cost.max_cloud_cost_per_day_eur", 0
            )
            if getattr(self, "policies", None)
            else 0,
            "filesystem_write": getattr(self.policies, "get", lambda *a, **k: None)(
                "filesystem.allow_delete", False
            )
            if getattr(self, "policies", None)
            else False,
        }

        ctx = {
            "agent_identity": {
                "role": getattr(self, "role", "Planner"),
                "agent_id": getattr(self, "agent_id", ""),
                "traits": getattr(self, "traits", {}),
            },
            "instincts": getattr(self, "instinct_text", ""),
            "policies": policies_snapshot,
            "preferences": prefs_snapshot,
            "recent_memory": recent_memory_snippets,
            "incoming_message": {
                "sender": msg_sender,
                "content": msg_content,
                "tags": msg_tags,
                "received_at_utc": datetime.datetime.now(datetime.UTC)
                .isoformat()
                .replace("+00:00", "Z"),
            },
            "task_hypothesis": task_hypothesis,
            "candidate_actions": candidate_actions,
            "escalation_policy": escalation_policy,
            "questions_for_reasoner": questions_for_reasoner,
        }

        return ctx

    async def reason_with_llm(self, llm_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: Ask the local LLM (via LLM Gateway) for a routing decision.

        Returns a dict with keys:
        - chosen_route: str
        - justification: str
        - confidence: float (0..1)
        - needs_user_confirmation: bool
        - _meta: { model_name, elapsed_ms }
        """
        client = LLMClient()
        system_prompt = (
            "You are the Planner's assistant. Return ONLY JSON with keys: "
            "chosen_route (string from candidate_actions), justification (string), "
            "confidence (0..1), needs_user_confirmation (true/false)."
        )

        result = await client.generate_reasoning(
            context_bundle=llm_ctx,
            system_prompt=system_prompt,
            tools=None,
            temperature=0.0,
            max_tokens=1024,
        )

        # Telemetry: prompt/response summary (redacted)
        if self.telemetry_collector:
            try:
                from core.message import Telemetry

                self.telemetry_collector.collect(
                    Telemetry(
                        agent_id=self.agent_id,
                        action="llm_prompt",
                        success=True,
                        cost=0.0,
                        duration_ms=result.get("elapsed_ms", 0),
                        metadata={"model": result.get("model_name", "unknown"), "context_keys": list(llm_ctx.keys())},
                    )
                )
                self.telemetry_collector.collect(
                    Telemetry(
                        agent_id=self.agent_id,
                        action="llm_response",
                        success=True,
                        cost=0.0,
                        duration_ms=0.0,
                        metadata={"model": result.get("model_name", "unknown"), "preview": (result.get("raw_text", "")[:200])},
                    )
                )
            except Exception:
                pass

        # Defaults (safe fallback)
        candidate_actions = llm_ctx.get("candidate_actions", [])
        default_route = candidate_actions[0] if candidate_actions else "Do nothing further and wait for approval."
        decision = {
            "chosen_route": default_route,
            "justification": "Fell back to deterministic default.",
            "confidence": 0.0,
            "needs_user_confirmation": True,
            "_meta": {
                "model_name": result.get("model_name", "unknown"),
                "elapsed_ms": result.get("elapsed_ms", 0),
            },
        }

        parsed = result.get("parsed_json")
        if isinstance(parsed, dict):
            try:
                ch = parsed.get("chosen_route")
                if ch and ch in candidate_actions:
                    decision["chosen_route"] = ch
                decision["justification"] = str(parsed.get("justification", decision["justification"]))
                # clamp confidence
                conf = float(parsed.get("confidence", 0.0))
                decision["confidence"] = max(0.0, min(1.0, conf))
                decision["needs_user_confirmation"] = bool(parsed.get("needs_user_confirmation", True))
            except Exception:
                # Keep defaults
                pass
        else:
            # Telemetry validation error
            if self.telemetry_collector:
                try:
                    from core.message import Telemetry

                    self.telemetry_collector.collect(
                        Telemetry(
                            agent_id=self.agent_id,
                            action="llm_validation_error",
                            success=False,
                            cost=0.0,
                            duration_ms=0.0,
                            metadata={"reason": "parsed_json is not a dict"},
                        )
                    )
                except Exception:
                    pass

        # Developer-facing print (Phase 2 dev UX)
        self.logger.info("\n— LLM DECISION (Planner) —")  # noqa: UP006
        self.logger.info("chosen_route: %s", decision["chosen_route"])  # noqa: UP006
        self.logger.info("justification: %s", decision["justification"])  # noqa: UP006
        self.logger.info("confidence: %.2f", decision["confidence"])  # noqa: UP006
        self.logger.info(
            "needs_user_confirmation: %s", "true" if decision["needs_user_confirmation"] else "false"
        )  # noqa: UP006
        self.logger.info(
            "model: %s, elapsed_ms: %s",
            decision["_meta"].get("model_name"),
            decision["_meta"].get("elapsed_ms"),
        )  # noqa: UP006

        return decision

    async def _approve_and_load_scaffold(self, manifest_path: str) -> None:
        """Run approval via Gatekeeper and sandbox-load the generated agent, then register it."""
        # Ask Gatekeeper for approval (non-ASK_USER path; the user already approved explicitly)
        req = ActionRequest(
            requester_agent_id=self.agent_id,
            requester_role=self.role,
            action_type=ActionType.AGENT_CREATION,
            details={"manifest_path": manifest_path},
            justification=f"Load generated agent from manifest {manifest_path}",
            user_impact="Enables new capability by loading generated scaffold",
            data_sensitivity=DataSensitivity.LOW,
            estimated_cost_eur=0.0,
            estimated_runtime_sec=1.0,
            reversibility=Reversibility.SOFT_REVERSIBLE,
            requires_user_approval=False,
        )

        try:
            approved, reason = await self.gatekeeper.evaluate_action(req)
        except Exception as e:
            await self.speak(
                content=f"Gatekeeper evaluation failed: {e}",
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )
            return

        if not approved or (isinstance(reason, str) and reason.startswith("ASK_USER")):
            await self.speak(
                content=f"Load not approved: {reason}",
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )
            return

        # Sandbox-load class
        try:
            loader = AgentLoader(Path("."))
            agent_class = loader.load_dynamic_agent(manifest_path)
            # Register dynamic agent in registry with provenance
            manifest = _json.loads(Path(manifest_path).read_text())
            if self.registry:
                self.registry.register_dynamic_agent(manifest)
            await self.speak(
                content=(
                    "Dynamic agent scaffold loaded and registered (quarantined).\n"
                    f"agent_name: {manifest.get('agent_name')}\nmanifest: {manifest_path}"
                ),
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )
        except Exception as e:
            await self.speak(
                content=f"Load failed: {e}",
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )

    async def _approve_and_activate_agent(self, agent_name: str) -> None:
        """Approve and activate a previously loaded (registered) dynamic agent.

        This instantiates the class, subscribes it to the bus, and marks it active.
        """
        # Gatekeeper approval (activation/spawn)
        req = ActionRequest(
            requester_agent_id=self.agent_id,
            requester_role=self.role,
            action_type=ActionType.PROCESS_SPAWN,
            details={"agent_name": agent_name},
            justification=f"Activate dynamic agent {agent_name}",
            user_impact="Enables new capability for routing",
            data_sensitivity=DataSensitivity.LOW,
            estimated_cost_eur=0.0,
            estimated_runtime_sec=1.0,
            reversibility=Reversibility.SOFT_REVERSIBLE,
            requires_user_approval=False,
        )

        try:
            approved, reason = await self.gatekeeper.evaluate_action(req)
        except Exception as e:
            await self.speak(
                content=f"Activation evaluation failed: {e}",
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )
            return

        if not approved or (isinstance(reason, str) and reason.startswith("ASK_USER")):
            await self.speak(
                content=f"Activation not approved: {reason}",
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )
            return

        # Resolve manifest for this agent
        manifest_path = Path(f"agents/dynamic/{agent_name}/MANIFEST.json")
        if not manifest_path.exists():
            await self.speak(
                content=f"Manifest not found for {agent_name}: {manifest_path}",
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )
            return

        try:
            # Load class
            loader = AgentLoader(Path("."))
            agent_class = loader.load_dynamic_agent(str(manifest_path))

            # Instantiate with system dependencies
            # Derive role from class name (strip version suffix if present)
            role = agent_name
            role = role[:-3] if role.endswith("_v1") else role

            new_agent = loader.create_agent_instance(
                agent_id=agent_name,
                role=role,
                agent_class=agent_class,
                registry=self.registry,
                message_bus=self.message_bus,
                preferences=self.preferences,
                policies=self.policies,
                telemetry_collector=self.telemetry_collector,
                memory_log=self.memory_log,
                gatekeeper=self.gatekeeper,
                logger=self.logger,
                name=agent_name,
                traits={"generated": True},
            )

            # Subscribe to bus
            if self.message_bus:
                self.message_bus.subscribe(new_agent.agent_id, new_agent.handle)

            # Activate in registry
            activated = self.registry.activate_agent(agent_name) if self.registry else False

            await self.speak(
                content=(
                    f"Agent {agent_name} activated and subscribed. "
                    f"Registry status: {'ok' if activated else 'not updated'}"
                ),
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )
        except Exception as e:
            await self.speak(
                content=f"Activation failed: {e}",
                recipient="user",
                message_type=MessageType.NOTIFICATION,
            )

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
