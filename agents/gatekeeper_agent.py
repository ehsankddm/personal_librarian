"""Gatekeeper Agent - Validates all real-world actions per ACTION_REQUEST.md."""

from typing import Optional, Dict, Any
from core.message import Message, MessageType
from agents.agent_core import Agent
from actions.action_request import ActionRequest
from core.gatekeeper import Gatekeeper
from core.llm_client import LLMClient


class GatekeeperAgent(Agent):
    """Agent responsible for safety and policy enforcement."""

    def __init__(self, gatekeeper: Gatekeeper, **kwargs):
        super().__init__(**kwargs)
        self.gatekeeper = gatekeeper

    async def can_handle(self, message: Message) -> bool:
        """Handle action approval requests."""
        if self.retired:
            return False

        return message.message_type == MessageType.REQUEST and "action_request" in message.metadata

    async def handle(self, message: Message) -> Optional[Message]:
        """
        Evaluate an action request per ACTION_REQUEST.md Section 4.

        Steps:
        1. Extract ActionRequest from message
        2. Evaluate via Gatekeeper
        3. If AUTO-APPROVE: execute and return success
        4. If ASK_USER: send approval request to user
        5. If DENY: return denial with reason
        """
        action_request = message.metadata.get("action_request")

        if not action_request or not isinstance(action_request, ActionRequest):
            response_content = "No valid action request provided."
            return Message(
                message_type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                content=response_content,
                receiver_id=message.sender_id,
            )

        # Evaluate via Gatekeeper
        approved, reason = await self.gatekeeper.evaluate_action(action_request)

        # Log evaluation
        self.log_event(
            {
                "type": "task_result",
                "success": approved and "ASK_USER" not in reason,
                "action_type": action_request.action_type.value
                if action_request.action_type
                else "unknown",
                "reason": reason,
                "request_id": action_request.request_id,
            }
        )

        # Handle different decision types
        if "ASK_USER" in reason:
            # Forward approval request to user
            return await self._request_user_approval(action_request, message.sender_id)
        elif approved:
            # Auto-approved, execute
            success, result = await self.gatekeeper.execute_action(action_request)

            if success:
                response_content = f"Gatekeeper: Request {action_request.request_id} executed successfully. {reason}"
            else:
                response_content = (
                    f"Gatekeeper: Request {action_request.request_id} failed: {result}"
                )

            return Message(
                message_type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                content=response_content,
                receiver_id=message.sender_id,
            )
        else:
            # Denied
            response_content = f"Denied: {reason}"

            # Log denial for retirement tracking
            self.log_event(
                {
                    "type": "task_result",
                    "success": False,
                    "action_type": action_request.action_type.value
                    if action_request.action_type
                    else "unknown",
                    "reason": reason,
                    "denied_for_policy": True,
                }
            )

            return Message(
                message_type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                content=response_content,
                receiver_id=message.sender_id,
            )

    async def _request_user_approval(
        self, action_request: ActionRequest, requester_id: str
    ) -> Message:
        """
        Request user approval per ACTION_REQUEST.md Section 4.3.

        Format:
        "BackupAgent_immediate_v5 wants to upload 3 encrypted files to Google Drive.
        Data sensitivity: medium (encrypted content only).
        Cost: €0.00.
        Irreversible: no.
        Approve? [yes/no]"
        """
        approval_message = f"""
{action_request.requester_agent_id} wants to perform: {action_request.action_type.value if action_request.action_type else "Unknown"}

Justification: {action_request.justification}

User Impact: {action_request.user_impact}
Data Sensitivity: {action_request.data_sensitivity.value if action_request.data_sensitivity else "Unknown"}
Cost: €{action_request.estimated_cost_eur:.2f}
Reversibility: {action_request.reversibility.value if action_request.reversibility else "Unknown"}

Approve? [yes/no]
Request ID: {action_request.request_id}
        """.strip()

        # Send to InterfaceAgent for user display
        await self.speak(
            content=approval_message,
            recipient="InterfaceAgent",
            message_type=MessageType.REQUEST,
            tags=["user_approval", "gatekeeper"],
        )

        # Also return acknowledgment to requester
        return Message(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            content=f"User approval requested for {action_request.request_id}. Waiting for response.",
            receiver_id=requester_id,
        )

    def describe_capabilities(self) -> str:
        """Describe what this agent can do."""
        return f"I am {self.agent_id}. I evaluate and approve/deny all risky actions for safety per ACTION_REQUEST.md."

    def analyze_action_request(self, action_request: ActionRequest) -> Dict[str, Any]:
        """
        Generate safety reasoning bundle for an action request.

        Per PHASE_1_ROADMAP §4: Creates structured analysis with who requested,
        what operation, cost, sensitivity, reversibility, policy gates, and decision.
        """
        # Build LLM context
        context = self.build_llm_context()

        # Extract safety info from action request
        estimated_cost = action_request.estimated_cost_eur if action_request else 0.0
        data_sensitivity = (
            action_request.data_sensitivity.value
            if action_request and action_request.data_sensitivity
            else "unknown"
        )
        reversibility = (
            action_request.reversibility.value
            if action_request and action_request.reversibility
            else "unknown"
        )
        action_type = (
            action_request.action_type.value
            if action_request and action_request.action_type
            else "unknown"
        )

        # Build safety bundle
        bundle = {
            "agent_identity": context["agent_identity"],
            "llm_context": context,
            "requesting_agent": action_request.requester_agent_id if action_request else "unknown",
            "requested_operation": action_type,
            "estimated_cost_eur": estimated_cost,
            "data_sensitivity": data_sensitivity,
            "reversibility": reversibility,
            "relevant_policy_gates": [],
            "proposed_decision": "Approve",
            "decision_reasoning": "Safe, low-cost, reversible operation",
        }

        # Add policy checks
        if self.policies:
            # Check network policy
            if (
                not self.policies.get("network.allow_external_requests", False)
                and "network" in action_type
            ):
                bundle["relevant_policy_gates"].append("Network requests disabled by policy")
                bundle["proposed_decision"] = "Deny"
                bundle["decision_reasoning"] = "Network operations are not allowed"

            # Check cost policy
            cost_limit = self.policies.get("cost.max_cloud_cost_per_day_eur", 0)
            if estimated_cost > cost_limit:
                bundle["relevant_policy_gates"].append(
                    f"Cost {estimated_cost} exceeds limit {cost_limit}"
                )
                bundle["proposed_decision"] = "Ask User"
                bundle["decision_reasoning"] = f"Estimated cost exceeds daily limit"

            # Check reversibility
            if reversibility in ["irreversible", "soft_reversible"]:
                bundle["relevant_policy_gates"].append(
                    "Irreversible operation requires explicit approval"
                )
                bundle["proposed_decision"] = "Ask User"
                bundle["decision_reasoning"] = "Operation cannot be fully reversed"

        return bundle

    async def advise_on(self, action_request: ActionRequest) -> Dict[str, Any]:
        """Phase 2: Ask LLM Gateway for a non-binding advisory rationale.

        Returns dict with keys: risk_summary, policy_refs, suggested_decision, user_prompt.
        """
        client = LLMClient()
        bundle = self.analyze_action_request(action_request)

        system_prompt = (
            "You are the safety advisor. Return ONLY JSON with keys: "
            "risk_summary (string), policy_refs (array of strings), "
            "suggested_decision ('approve'|'deny'|'escalate'), user_prompt (string)."
        )

        result = await client.generate_reasoning(
            context_bundle=bundle,
            system_prompt=system_prompt,
            tools=None,
            temperature=0.0,
            max_tokens=1024,
        )

        advisory = {
            "risk_summary": "",
            "policy_refs": [],
            "suggested_decision": "escalate",
            "user_prompt": "",
            "_meta": {"model_name": result.get("model_name", "unknown"), "elapsed_ms": result.get("elapsed_ms", 0)},
        }
        parsed = result.get("parsed_json")
        if isinstance(parsed, dict):
            try:
                advisory["risk_summary"] = str(parsed.get("risk_summary", ""))
                pr = parsed.get("policy_refs") or []
                advisory["policy_refs"] = [str(x) for x in pr if isinstance(x, str)]
                sd = str(parsed.get("suggested_decision", "escalate")).lower()
                if sd in {"approve", "deny", "escalate"}:
                    advisory["suggested_decision"] = sd
                advisory["user_prompt"] = str(parsed.get("user_prompt", ""))
            except Exception:
                pass

        # Telemetry: record prompt/response
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
                        metadata={"model": result.get("model_name", "unknown"), "context_keys": list(bundle.keys())},
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

        # Dev print only
        self.logger.info("\n— LLM ADVISORY (Gatekeeper) —")  # noqa: UP006
        self.logger.info("suggested_decision: %s", advisory["suggested_decision"])  # noqa: UP006
        self.logger.info("risk_summary: %s", advisory["risk_summary"])  # noqa: UP006
        if advisory["policy_refs"]:
            self.logger.info("policy_refs: %s", ", ".join(advisory["policy_refs"]))  # noqa: UP006
        return advisory
