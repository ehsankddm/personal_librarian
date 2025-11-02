"""Evaluator - Evaluates agent and system performance."""

from typing import Dict, Any, List
from learning.telemetry_collector import TelemetryCollector
from learning.reward_engine import RewardEngine
from core.registry import Registry


class Evaluator:
    """Evaluates agent and system performance."""

    def __init__(
        self,
        telemetry_collector: TelemetryCollector,
        reward_engine: RewardEngine,
        registry: Registry,
    ):
        self.telemetry_collector = telemetry_collector
        self.reward_engine = reward_engine
        self.registry = registry

    def evaluate_agent(self, agent_id: str) -> Dict[str, Any]:
        """Evaluate an agent's performance."""
        telemetry = self.telemetry_collector.query(agent_id=agent_id)

        if not telemetry:
            return {"error": "No telemetry data"}

        total_reward = sum(self.reward_engine.calculate_reward(entry) for entry in telemetry)
        success_rate = sum(entry["success"] for entry in telemetry) / len(telemetry)
        avg_cost = sum(entry["cost"] for entry in telemetry) / len(telemetry)

        agent_info = self.registry.get_agent(agent_id)

        return {
            "agent_id": agent_id,
            "role": agent_info.role if agent_info else "unknown",
            "total_reward": total_reward,
            "success_rate": success_rate,
            "avg_cost": avg_cost,
            "total_actions": len(telemetry),
        }

    def evaluate_system(self) -> Dict[str, Any]:
        """Evaluate overall system performance."""
        agents = self.registry.get_agents()

        results = {}
        for agent_id in agents:
            results[agent_id] = self.evaluate_agent(agent_id)

        return results

    def get_top_performers(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get top performing agents."""
        evaluations = self.evaluate_system()
        sorted_agents = sorted(
            evaluations.items(), key=lambda x: x[1].get("total_reward", 0), reverse=True
        )
        return sorted_agents[:n]
