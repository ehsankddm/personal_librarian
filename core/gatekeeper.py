"""Gatekeeper - Validates and executes all real-world actions per ACTION_REQUEST.md."""

from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging

from actions.action_request import ActionRequest, Reversibility, DataSensitivity
from core.policies import PolicyManager
from actions.executor import ActionExecutor


@dataclass
class GatekeeperDecision:
    """Result of Gatekeeper evaluation."""
    approved: bool
    ask_user: bool  # True if needs user approval
    reason: str
    constraints: dict[str, Any]


class Gatekeeper:
    """
    Enforces safety and policy boundaries per ACTION_REQUEST.md Section 4.
    
    Gatekeeper is the authority for all real-world actions.
    Every agent must go through this chokepoint.
    """
    
    def __init__(self, policy_manager: PolicyManager, executor: ActionExecutor):
        self.policy_manager = policy_manager
        self.executor = executor
        self.audit_log_path = Path("logs/audit_actions.log")
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        self.logger = logging.getLogger("gatekeeper")
        handler = logging.FileHandler(self.audit_log_path)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def evaluate_action(self, request: ActionRequest) -> tuple[bool, str]:
        """
        Evaluate an action request per ACTION_REQUEST.md Section 4.1.
        
        Args:
            request: The action request to evaluate
            
        Returns:
            (approved: bool, reason: str)
        """
        decision = await self._evaluate_request(request)
        
        # Log decision
        self.logger.info(
            f"Request {request.request_id}: "
            f"{'APPROVED' if decision.approved and not decision.ask_user else 'ASK_USER' if decision.ask_user else 'DENIED'} - "
            f"{decision.reason}"
        )
        
        if decision.approved and not decision.ask_user:
            return True, decision.reason
        elif decision.ask_user:
            return True, f"ASK_USER: {decision.reason}"
        else:
            return False, decision.reason
    
    async def _evaluate_request(self, request: ActionRequest) -> GatekeeperDecision:
        """
        Internal evaluation logic per ACTION_REQUEST.md Section 4.1.
        
        Steps:
        1. Validate action_type and details shape
        2. Check policies.json
        3. Check reversibility and sensitivity levels
        4. Decide: AUTO-APPROVE, ASK_USER, or DENY
        """
        
        # Step 1: Validate action_type and details
        if not request.action_type:
            return GatekeeperDecision(
                approved=False,
                ask_user=False,
                reason="Invalid action type: missing",
                constraints={}
            )
        
        # Step 2: Check policies
        policy_allowed, constraints = self.policy_manager.check(request.action_type.value)
        if not policy_allowed:
            return GatekeeperDecision(
                approved=False,
                ask_user=False,
                reason=f"Policy violation: {request.action_type.value} is not allowed",
                constraints=constraints
            )
        
        # Step 3: Check cost constraints
        if request.estimated_cost_eur > constraints.get("max_cost_eur", float('inf')):
            return GatekeeperDecision(
                approved=False,
                ask_user=False,
                reason=f"Cost exceeds policy limit: €{request.estimated_cost_eur}",
                constraints=constraints
            )
        
        # Step 4: Check reversibility and sensitivity
        requires_approval = self._requires_user_approval(request)
        
        if requires_approval:
            return GatekeeperDecision(
                approved=True,
                ask_user=True,
                reason=self._format_user_approval_request(request),
                constraints=constraints
            )
        
        # AUTO-APPROVE
        return GatekeeperDecision(
            approved=True,
            ask_user=False,
            reason="Auto-approved per policy",
            constraints=constraints
        )
    
    def _requires_user_approval(self, request: ActionRequest) -> bool:
        """
        Determine if user approval is required per ACTION_REQUEST.md.
        
        Rules:
        - Agent explicitly requested approval
        - Action is irreversible
        - Data sensitivity is high
        - Combination of medium+ sensitivity + irreversible
        """
        # Agent explicitly requested
        if request.requires_user_approval:
            return True
        
        # Irreversible action
        if request.reversibility == Reversibility.IRREVERSIBLE:
            return True
        
        # High sensitivity data
        if request.data_sensitivity == DataSensitivity.HIGH:
            return True
        
        # Medium sensitivity + irreversible
        if (request.data_sensitivity == DataSensitivity.MEDIUM and 
            request.reversibility == Reversibility.IRREVERSIBLE):
            return True
        
        return False
    
    def _format_user_approval_request(self, request: ActionRequest) -> str:
        """Format human-readable approval request per ACTION_REQUEST.md Section 4.3."""
        return request.get_human_readable_summary()
    
    async def execute_action(self, request: ActionRequest) -> tuple[bool, Any]:
        """
        Execute an approved action per ACTION_REQUEST.md Section 4.2.
        
        Args:
            request: The approved action request
            
        Returns:
            (success: bool, result: Any)
        """
        # Log execution
        self.logger.info(f"Executing request {request.request_id}")
        
        # Execute via executor
        success, result = await self.executor.execute(request)
        
        # Log result
        if success:
            self.logger.info(f"Request {request.request_id} completed successfully")
        else:
            self.logger.error(f"Request {request.request_id} failed: {result}")
        
        return success, result
    
    def log_decision(self, request: ActionRequest, decision: GatekeeperDecision):
        """Log the gatekeeper's decision for audit trail."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request.request_id,
            "requester": request.requester_agent_id,
            "action_type": request.action_type.value if request.action_type else None,
            "approved": decision.approved,
            "ask_user": decision.ask_user,
            "reason": decision.reason,
        }
        
        self.logger.info(f"Decision: {log_entry}")
