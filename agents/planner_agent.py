"""Planner Agent - Coordinates and routes tasks per PLANNER.md."""

from typing import Optional
from core.message import Message, MessageType
from agents.agent_core import Agent
from core.planner import Planner


class PlannerAgent(Agent):
    """
    Agent responsible for coordination and task routing.
    
    This is the wrapper agent that uses the core Planner logic.
    """
    
    def __init__(self, planner: Planner, **kwargs):
        super().__init__(**kwargs)
        self.planner = planner
    
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
            message.message_type in [MessageType.REQUEST, MessageType.ESCALATION] or
            message.receiver_id == "Planner" or
            message.receiver_id == self.agent_id or
            "route" in message.content.lower() or
            "coordinate" in message.content.lower()
        )
    
    async def handle(self, message: Message) -> Optional[Message]:
        """
        Route message using Planner core logic.
        Per PLANNER.md Section 5 workflow.
        """
        # Delegate to Planner's receive_message
        response = await self.planner.receive_message(message)
        
        # Log telemetry
        self.log_event({
            'type': 'message_exchange',
            'success': True,
            'routed': True,
            'message_sender': message.sender_id
        })
        
        return response
    
    def describe_capabilities(self) -> str:
        """
        Describe what this agent can do.
        Per PLANNER.md Section 1.
        """
        return (
            f"I am {self.agent_id}. I am the central coordinator and router. "
            f"I ensure every request finds the right executor safely and efficiently, "
            f"generate new agents when capabilities are missing, and continuously learn "
            f"which routing patterns produce the best results."
        )
