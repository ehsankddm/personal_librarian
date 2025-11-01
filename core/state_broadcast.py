"""State Broadcast - Distribute system state changes to all agents."""

from typing import Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum


class StateEvent(str, Enum):
    """Types of state changes."""
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    POLICY_UPDATED = "policy_updated"
    PREFERENCE_UPDATED = "preference_updated"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"


@dataclass
class StateUpdate:
    """A state update notification."""
    event_type: StateEvent
    timestamp: str
    data: Dict[str, Any]


class StateBroadcaster:
    """Broadcasts state changes to subscribed agents."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, agent_id: str, handler: Callable[[StateUpdate], None]):
        """Subscribe an agent to state updates."""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(handler)
    
    def unsubscribe(self, agent_id: str, handler: Callable):
        """Unsubscribe an agent from state updates."""
        if agent_id in self.subscribers:
            self.subscribers[agent_id].remove(handler)
    
    async def broadcast(self, event_type: StateEvent, data: Dict[str, Any]):
        """Broadcast a state change to all subscribers."""
        update = StateUpdate(
            event_type=event_type,
            timestamp=data.get('timestamp', ''),
            data=data
        )
        
        for handlers in self.subscribers.values():
            for handler in handlers:
                await handler(update)

