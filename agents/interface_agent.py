"""Interface Agent - Handles user chat, feedback, and escalation per specifications."""

from typing import Optional
from core.message import Message, MessageType
from agents.agent_core import Agent


class InterfaceAgent(Agent):
    """
    Agent that interfaces with the user.

    Per Phase 0:
    - Accepts user utterances via stdin or harness
    - Wraps them into Messages addressed to Planner
    - Receives messages destined for "User" and prints them
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation_history = []

    async def can_handle(self, message: Message) -> bool:
        """
        Interface agent handles:
        1. Messages from "user" (to route to Planner)
        2. Messages with receiver_id="User" or "user" (to display)
        3. Messages addressed to InterfaceAgent_main_v1 (may be from Planner)
        """
        if self.retired:
            return False

        # Handle messages from user
        if message.sender_id == "user":
            return True

        # Handle messages to user
        if message.receiver_id in ["User", "user"]:
            return True

        # Handle messages to InterfaceAgent (from Planner)
        if message.receiver_id == self.agent_id:
            return True

        return False

    async def handle(self, message: Message) -> Optional[Message]:
        """
        Process user message and route to Planner.

        For messages FROM user:
        - Wrap in Message addressed to Planner
        - Publish to bus

        For messages TO user:
        - Print to stdout
        - Log conversation
        """
        if self.retired:
            return None

        # Case 1: Message FROM user - route to Planner
        if message.sender_id == "user" and message.receiver_id is None:
            self.conversation_history.append({"from": "user", "content": message.content})

            # Log
            self.log_event(
                {
                    "type": "message_exchange",
                    "success": True,
                    "from": "user",
                    "message_length": len(message.content),
                }
            )

            # Route to Planner
            planner_message = Message(
                message_type=MessageType.REQUEST,
                sender_id=self.agent_id,
                content=message.content,
                receiver_id="Planner",
                tags=["user_request"],
            )

            # Publish to bus with direct dispatch for immediate processing
            if self.message_bus:
                await self.message_bus.publish(planner_message, direct_dispatch=True)

            # Do NOT return acknowledgment that would trigger user message loop
            # InterfaceAgent is a sink for user messages - render and stop
            return None

        # Case 2: Message TO user - display
        if message.receiver_id in ["User", "user"]:
            # Print to stdout
            print(f"\n[{message.sender_id}]")
            print(message.content)
            print()

            # Log conversation
            self.conversation_history.append(
                {"from": message.sender_id, "content": message.content}
            )

            # Log event
            self.log_event(
                {
                    "type": "message_exchange",
                    "success": True,
                    "to": "user",
                    "sender": message.sender_id,
                }
            )

            return None

        # Case 3: Message to InterfaceAgent_main_v1 (from Planner) - display to user
        if message.receiver_id == self.agent_id:
            # Display as if from Planner to user
            print(f"\n[{message.sender_id}]")
            print(message.content)
            print()

            # Log conversation
            self.conversation_history.append(
                {"from": message.sender_id, "content": message.content}
            )

            # Log event
            self.log_event(
                {
                    "type": "message_exchange",
                    "success": True,
                    "to": "user",
                    "sender": message.sender_id,
                }
            )

            return None

    def describe_capabilities(self) -> str:
        """Describe what this agent can do."""
        return (
            f"I am {self.agent_id}. I handle user input and route it to Planner. "
            f"I also display messages destined for the user."
        )

    async def collect_feedback(self, feedback: str):
        """Collect and process user feedback."""
        # TODO: Update preferences, reward agents, etc.
        pass

    def send_to_user(self, content: str):
        """Helper to send message to user (prints to stdout)."""
        print(f"\n[{self.agent_id}] {content}\n")
