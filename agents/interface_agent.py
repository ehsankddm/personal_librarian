"""Interface Agent - Handles user chat, feedback, and escalation."""

from typing import Optional
from core.message import Message, MessageType
from agents.agent_core import Agent


class InterfaceAgent(Agent):
    """Agent that interfaces with the user."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation_history = []
    
    async def can_handle(self, message: Message) -> bool:
        """Interface agent handles all user messages."""
        if self.retired:
            return False
        return message.message_type == MessageType.REQUEST and message.sender_id == "user"
    
    async def handle(self, message: Message) -> Optional[Message]:
        """Process user message and route to appropriate agents."""
        if self.retired:
            return None
        
        self.conversation_history.append(message.content)
        
        # Log message exchange
        self.log_event({
            'type': 'message_exchange',
            'success': True,
            'message_length': len(message.content)
        })
        
        # TODO: Use planner to route to appropriate agent
        # For now, echo back
        response_content = f"I received: {message.content}. Processing..."
        
        # Create response message
        response = Message(
            message_type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            content=response_content,
            receiver_id=message.sender_id
        )
        
        return response
    
    def describe_capabilities(self) -> str:
        """Describe what this agent can do."""
        return f"I am {self.agent_id}. I handle user input and route it to appropriate agents."
    
    async def collect_feedback(self, feedback: str):
        """Collect and process user feedback."""
        # TODO: Update preferences, reward agents, etc.
        pass

