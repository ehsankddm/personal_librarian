"""Policies - Hard technical rules and constraints."""

from typing import Dict, Any
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class Policy:
    """A policy rule."""
    name: str
    action_type: str
    allowed: bool
    constraints: Dict[str, Any]


class PolicyManager:
    """Manages policy rules."""
    
    def __init__(self, policies_path: str = "state/policies.json"):
        self.policies_path = Path(policies_path)
        self.policies: Dict[str, Policy] = {}
        self.load_defaults()
        self.load_from_file()
    
    def load_defaults(self):
        """Load default safety policies."""
        default_policies = [
            Policy(
                name="no_file_deletion",
                action_type="file_delete",
                allowed=False,
                constraints={}
            ),
            Policy(
                name="network_timeout",
                action_type="network_request",
                allowed=True,
                constraints={"max_timeout_seconds": 30}
            ),
            Policy(
                name="cost_limit",
                action_type="costly_operation",
                allowed=True,
                constraints={"max_cost": 1.0}
            ),
        ]
        
        for policy in default_policies:
            self.policies[policy.name] = policy
    
    def load_from_file(self):
        """Load policies from JSON file."""
        if self.policies_path.exists():
            with open(self.policies_path, 'r') as f:
                data = json.load(f)
                for policy_data in data.get('policies', []):
                    policy = Policy(**policy_data)
                    self.policies[policy.name] = policy
    
    def save_to_file(self):
        """Save policies to JSON file."""
        data = {
            'policies': [
                {
                    'name': p.name,
                    'action_type': p.action_type,
                    'allowed': p.allowed,
                    'constraints': p.constraints
                }
                for p in self.policies.values()
            ]
        }
        
        self.policies_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.policies_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def check(self, action_type: str) -> tuple[bool, Dict[str, Any]]:
        """Check if an action is allowed."""
        # Find relevant policies
        for policy in self.policies.values():
            if policy.action_type == action_type:
                if not policy.allowed:
                    return False, policy.constraints
                return True, policy.constraints
        
        # Default: deny unknown actions
        return False, {}
    
    def add_policy(self, policy: Policy):
        """Add or update a policy."""
        self.policies[policy.name] = policy
        self.save_to_file()

