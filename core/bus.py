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
    
    async def publish(self, message: Message):
        """Publish a message to the bus."""
        if not message.message_id:
            message.message_id = f"{message.sender_id}_{datetime.now().isoformat()}"
        
        await self.queue.put(message)
        self.message_history.append(message)
    
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
        # If specific receiver, send only to that agent
        if message.receiver_id:
            if message.receiver_id in self.subscribers:
                for handler in self.subscribers[message.receiver_id]:
                    try:
                        await handler(message)
                    except Exception as e:
                        print(f"Error in handler for {message.receiver_id}: {e}")
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
                    print(f"Error in handler for {agent_id}: {e}")
    
    def stop(self):
        """Stop the message bus."""
        self.running = False
    
    def get_message_count(self) -> int:
        """Get total number of messages processed."""
        return len(self.message_history)
