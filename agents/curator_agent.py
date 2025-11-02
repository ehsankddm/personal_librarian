"""Curator Agent - Reads telemetry and updates preferences/policies."""

from typing import Optional
from core.message import Message, MessageType
from agents.agent_core import Agent


class CuratorAgent(Agent):
    """Agent responsible for learning and adaptation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.telemetry_history = []

    async def can_handle(self, message: Message) -> bool:
        """Handle telemetry and learning-related messages."""
        if self.retired:
            return False

        return (
            message.message_type == MessageType.TELEMETRY
            or "curate" in message.content.lower()
            or "learn" in message.content.lower()
        )

    async def handle(self, message: Message) -> Optional[Message]:
        """Process telemetry and update learning."""
        # TODO: Implement preference learning and policy updates
        response_content = "Telemetry processed. Learning updated."

        # Log processing
        self.log_event({"type": "message_exchange", "success": True, "telemetry_processed": True})

        return Message(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            content=response_content,
            receiver_id=message.sender_id,
        )

    def describe_capabilities(self) -> str:
        """Describe what this agent can do."""
        return f"I am {self.agent_id}. I analyze telemetry and update preferences and policies."

    async def analyze_performance(self):
        """Analyze agent performance and update routing preferences."""
        # TODO: Read registry stats, update planner routing
        pass
