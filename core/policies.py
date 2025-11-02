"""Policies - Hard technical rules and constraints per specifications."""

from typing import Dict, Any, Optional
import json
from pathlib import Path


class PolicyManager:
    """Manages policy rules from state/policies.json."""

    def __init__(self, policies_path: str = "state/policies.json"):
        self.policies_path = Path(policies_path)
        self.policies: Dict[str, Any] = {}
        self.locks: Dict[str, str] = {}
        self.load_from_file()

    def load_from_file(self):
        """Load policies from JSON file."""
        if not self.policies_path.exists():
            # Use defaults if file doesn't exist
            self._load_defaults()
            return

        with open(self.policies_path, "r") as f:
            data = json.load(f)
            self.policies = {k: v for k, v in data.items() if not k.startswith("_")}
            self.locks = data.get("_locks", {})

    def _load_defaults(self):
        """Load default policies."""
        self.policies = {
            "network": {"allow_external_requests": False, "allowed_domains": []},
            "filesystem": {"allow_delete": False},
            "cost": {"max_cloud_cost_per_day_eur": 0},
        }
        self.locks = {
            "filesystem.allow_delete": "user_only",
            "cost.max_cloud_cost_per_day_eur": "user_only",
        }
        self.save_to_file()

    def save_to_file(self):
        """Save policies to JSON file."""
        data = {**self.policies, "_locks": self.locks}

        self.policies_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.policies_path, "w") as f:
            json.dump(data, f, indent=2)

    def check(self, action_type: str) -> tuple[bool, Dict[str, Any]]:
        """
        Check if an action type is allowed.
        Returns (allowed, constraints)
        """
        # Map action types to policy sections
        action_to_policy = {
            "network.fetch": ("network", "allow_external_requests", False),
            "network.upload": ("network", "allow_external_requests", False),
            "filesystem.delete": ("filesystem", "allow_delete", False),
            "filesystem.write": ("filesystem", None, True),  # Always allowed
            "backup.sync": ("cost", None, True),  # Allowed, cost checked separately
            "compute.heavy": ("cost", None, True),  # Allowed, cost checked separately
            "delivery.kindle_send": (
                "network",
                None,
                True,
            ),  # Allowed, just records network section
            "metadata.lookup_external": ("network", "allow_external_requests", False),
            "process.spawn": ("filesystem", None, True),  # Always allowed
            "agent_creation": ("filesystem", None, True),  # Always allowed
        }

        if action_type not in action_to_policy:
            # Unknown action type - default to allowed
            return True, {}

        section, key, default = action_to_policy[action_type]
        constraints = self.policies.get(section, {})

        if key is None:
            # No specific check needed - return allowed with constraints
            return default, constraints

        # Check the specific policy key
        allowed = constraints.get(key, False)
        return allowed, constraints

    def get(self, path: str, default: Any = None) -> Any:
        """Get a policy value by dot-path."""
        parts = path.split(".")
        value = self.policies
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default
        return value

    def is_locked(self, path: str) -> bool:
        """Check if a policy path is locked."""
        return path in self.locks

    def get_lock_type(self, path: str) -> Optional[str]:
        """Get the lock type for a policy path."""
        return self.locks.get(path)

    def set(self, path: str, value: Any, check_lock: bool = True) -> bool:
        """
        Set a policy value by dot-path.
        Returns True if set successfully, False if locked.
        """
        if check_lock and self.is_locked(path):
            return False

        parts = path.split(".")
        # Navigate/create nested structure
        current = self.policies
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

        self.save_to_file()
        return True

    def add_domain_to_whitelist(self, domain: str):
        """Add a domain to the network whitelist."""
        if "network" not in self.policies:
            self.policies["network"] = {}
        if "allowed_domains" not in self.policies["network"]:
            self.policies["network"]["allowed_domains"] = []

        if domain not in self.policies["network"]["allowed_domains"]:
            self.policies["network"]["allowed_domains"].append(domain)
            self.save_to_file()
