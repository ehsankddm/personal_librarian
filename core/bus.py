"""Message Bus - Shared async queue for all agent communications per PLANNER.md."""

import asyncio
from typing import Callable, Any
from datetime import datetime

from core.message import Message


class MessageBus:
    """
    Async message bus for agent coordination.

    Central communication backbone where all agents publish and subscribe to messages.
    """

    def __init__(self):
        self.queue = asyncio.Queue()
        self.subscribers: dict[str, list[Callable]] = {}
        self.message_history: list[Message] = []
        self.running = False

    async def publish(self, message: Message, direct_dispatch: bool = False):
        """
        Publish a message to the bus.

        Args:
            message: Message to publish
            direct_dispatch: If True, dispatch immediately instead of queuing
        """
        # Force queued delivery for user-directed messages to prevent loops
        if message.receiver_id in ["User", "user"]:
            direct_dispatch = False

        if not message.message_id:
            message.message_id = f"{message.sender_id}_{datetime.now().isoformat()}"

        self.message_history.append(message)

        if direct_dispatch:
            await self._dispatch(message)
        else:
            await self.queue.put(message)

    def subscribe(self, agent_id: str, handler: Callable):
        """Subscribe an agent to receive messages."""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(handler)

    def unsubscribe(self, agent_id: str, handler: Callable):
        """Unsubscribe an agent from messages."""
        if agent_id in self.subscribers:
            try:
                self.subscribers[agent_id].remove(handler)
            except ValueError:
                pass  # Handler not in list

    async def start(self):
        """Start the message bus loop."""
        self.running = True
        while self.running:
            try:
                message = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._dispatch(message)
            except asyncio.TimeoutError:
                continue  # Keep running
            except Exception as e:
                # Log error but keep running
                print(f"Error in message bus: {e}")
                continue

    async def _dispatch(self, message: Message):
        """Dispatch message to appropriate subscribers."""
        # Log message
        print(
            f"[Message Bus] {message.sender_id} -> {message.receiver_id or 'broadcast'}: {message.content[:80]}",
            flush=True,
        )

        # If specific receiver, send only to that agent
        if message.receiver_id:
            if message.receiver_id in self.subscribers:
                for handler in self.subscribers[message.receiver_id]:
                    try:
                        response = await handler(message)
                        # If handler returns a message, publish it
                        if response:
                            await self.publish(response, direct_dispatch=True)
                    except Exception as e:
                        print(f"Error in handler for {message.receiver_id}: {e}", flush=True)
            else:
                print(f"[Message Bus] Warning: No subscriber for {message.receiver_id}", flush=True)
            return

        # Otherwise broadcast to all subscribers
        for agent_id, handlers in self.subscribers.items():
            # Skip sender
            if agent_id == message.sender_id:
                continue

            for handler in handlers:
                try:
                    await handler(message)
                except Exception as e:
                    print(f"Error in handler for {agent_id}: {e}", flush=True)

    def stop(self):
        """Stop the message bus."""
        self.running = False

    def get_message_count(self) -> int:
        """Get total number of messages processed."""
        return len(self.message_history)
