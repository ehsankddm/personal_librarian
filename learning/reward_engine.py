"""Reward Engine - Converts telemetry into scalar rewards."""

from typing import Dict, Any
from core.message import Telemetry


class RewardEngine:
    """Converts telemetry into scalar rewards for learning."""
    
    def __init__(self):
        self.reward_weights = {
            'success': 1.0,
            'cost_penalty': -0.5,
            'time_penalty': -0.01,
            'safety_bonus': 2.0,
        }
    
    def calculate_reward(self, telemetry: Telemetry) -> float:
        """Calculate scalar reward from telemetry."""
        reward = 0.0
        
        # Success/failure
        if telemetry.success:
            reward += self.reward_weights['success']
        else:
            reward -= self.reward_weights['success']
        
        # Cost penalty
        reward -= telemetry.cost * self.reward_weights['cost_penalty']
        
        # Time penalty (normalized to seconds)
        time_seconds = telemetry.duration_ms / 1000
        reward -= time_seconds * self.reward_weights['time_penalty']
        
        # Safety bonus
        safety = telemetry.metadata.get('safety_score', 0.0)
        reward += safety * self.reward_weights['safety_bonus']
        
        return reward
    
    def update_weights(self, weights: Dict[str, float]):
        """Update reward weights."""
        self.reward_weights.update(weights)

