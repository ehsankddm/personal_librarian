"""Router Learner - Learns optimal message routing strategies."""

from typing import Dict, Any
from core.registry import Registry


class RouterLearner:
    """Learns optimal routing strategies for the planner."""

    def __init__(self, registry: Registry):
        self.registry = registry
        self.routing_history: list[Dict[str, Any]] = []

    def record_routing(self, message_content: str, target_agent: str, success: bool):
        """Record a routing decision and its outcome."""
        self.routing_history.append(
            {
                "content": message_content,
                "target": target_agent,
                "success": success,
            }
        )

    def recommend_agent(self, message_content: str) -> str:
        """Recommend an agent for a given message."""
        # TODO: Use history to recommend best agent
        # For now, return None
        return None

    def analyze_performance(self) -> Dict[str, float]:
        """Analyze routing performance statistics."""
        if not self.routing_history:
            return {}

        success_rate = sum(h["success"] for h in self.routing_history) / len(self.routing_history)

        return {
            "success_rate": success_rate,
            "total_routes": len(self.routing_history),
        }
