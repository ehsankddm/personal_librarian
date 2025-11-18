"""Registry & Replica Management - Complete implementation per REGISTRY.md specification."""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from pathlib import Path


@dataclass
class SafetyProfile:
    """Safety profile for an agent replica."""

    needs_network: bool = False
    touches_user_data: bool = False
    irreversible_ops_possible: bool = False


@dataclass
class PerformanceMetrics:
    """Performance tracking for an agent replica."""

    success_count: int = 0
    failure_count: int = 0
    escalation_count: int = 0
    avg_reward: float = 0.0
    avg_latency_sec: float = 0.0
    last_reward: float = 0.0

    def update_reward(self, reward: float):
        """Update average reward using exponential moving average."""
        if self.success_count == 0:
            self.avg_reward = reward
        else:
            # EMA with alpha=0.1
            self.avg_reward = 0.9 * self.avg_reward + 0.1 * reward
        self.last_reward = reward


@dataclass
class AgentInfo:
    """
    Complete information about an agent replica per REGISTRY.md Section 4.
    """

    agent_id: str
    role: str

    traits: Dict[str, Any] = field(default_factory=dict)
    instinct_paths: List[str] = field(default_factory=list)

    status: str = "active"  # "active" | "quarantined" | "retired"
    alive: bool = True  # Runtime liveness flag

    capabilities_summary: str = ""

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_active_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    retired_at: Optional[str] = None
    retire_reason: Optional[str] = None

    safety_profile: SafetyProfile = field(default_factory=SafetyProfile)
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        # Convert SafetyProfile and PerformanceMetrics to dicts
        d["safety_profile"] = asdict(self.safety_profile)
        d["performance"] = asdict(self.performance)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInfo":
        """Create from dictionary."""
        # Handle nested dataclasses
        if isinstance(data.get("safety_profile"), dict):
            data["safety_profile"] = SafetyProfile(**data["safety_profile"])
        if isinstance(data.get("performance"), dict):
            data["performance"] = PerformanceMetrics(**data["performance"])
        return cls(**data)


class Registry:
    """
    Registry & Replica Management per REGISTRY.md.

    Source of truth for:
    - Which agents exist
    - Which replicas are active
    - What each replica can do
    - How well each replica performs
    - Which replicas are allowed to receive work
    - Which replicas have been retired
    """

    def __init__(self, persistence_path: str = "state/registry_state.json"):
        self.persistence_path = Path(persistence_path)
        self.agents: Dict[str, AgentInfo] = {}
        self.roles: Dict[str, List[str]] = {}  # role -> [agent_ids]

        # Ensure state directory exists
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing state
        self.load_state()

    # === Persistence ===

    def save_state(self):
        """Persist registry state to disk."""
        data = {
            "agents": {agent_id: agent.to_dict() for agent_id, agent in self.agents.items()},
            "last_updated": datetime.now(UTC).isoformat(),
        }
        self.persistence_path.write_text(json.dumps(data, indent=2))

    def load_state(self):
        """Load registry state from disk."""
        if not self.persistence_path.exists():
            return

        data = json.loads(self.persistence_path.read_text())
        agents_data = data.get("agents", {})

        for agent_id, agent_data in agents_data.items():
            try:
                agent_info = AgentInfo.from_dict(agent_data)
                self.agents[agent_id] = agent_info

                # Update role index
                role = agent_info.role
                if role not in self.roles:
                    self.roles[role] = []
                if agent_id not in self.roles[role]:
                    self.roles[role].append(agent_id)

                # Set alive status based on status field
                if agent_info.status == "retired":
                    agent_info.alive = False
                else:
                    agent_info.alive = True
            except Exception as e:
                print(f"Error loading agent {agent_id}: {e}")

    # === Core Operations ===

    def register_agent(
        self,
        agent_id: str,
        role: str,
        capabilities_summary: str,
        traits: Dict[str, Any] = None,
        instinct_paths: List[str] = None,
        safety_profile: SafetyProfile = None,
        status: str = "active",
        society_memory=None,
    ) -> None:
        """
        Register a new agent replica.
        Per REGISTRY.md Section 5.1
        """
        # Validation
        if not agent_id:
            raise ValueError("agent_id must be provided")
        if not role:
            raise ValueError("role must be provided")
        if not capabilities_summary:
            raise ValueError("capabilities_summary must be provided")
        if agent_id in self.agents:
            raise ValueError(f"agent_id {agent_id} already exists")

        if status not in ["active", "quarantined"]:
            raise ValueError(f"New agents must start as 'active' or 'quarantined', not '{status}'")

        # Create agent info
        agent_info = AgentInfo(
            agent_id=agent_id,
            role=role,
            traits=traits or {},
            instinct_paths=instinct_paths or [],
            status=status,
            alive=(status != "retired"),
            capabilities_summary=capabilities_summary,
            safety_profile=safety_profile or SafetyProfile(),
        )

        # Add to registry
        self.agents[agent_id] = agent_info

        # Update role index
        if role not in self.roles:
            self.roles[role] = []
        self.roles[role].append(agent_id)

        # Persist
        self.save_state()

        # Log to society memory
        if society_memory:
            traits_str = ", ".join(f"{k}={v}" for k, v in (traits or {}).items())
            society_memory.add_entry(
                f"Registered new agent {agent_id} (role={role}, traits={traits_str})."
            )

    def update_performance(
        self,
        agent_id: str,
        reward_delta: float = 0.0,
        success: bool = False,
        latency_sec: float = 0.0,
        escalated: bool = False,
    ) -> None:
        """
        Update performance metrics after task completion.
        Per REGISTRY.md Section 5.2
        """
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]

        # Update counters
        if success:
            agent.performance.success_count += 1
        else:
            agent.performance.failure_count += 1

        if escalated:
            agent.performance.escalation_count += 1

        # Update reward
        if reward_delta != 0.0:
            agent.performance.update_reward(reward_delta)

        # Update latency
        if latency_sec > 0:
            total_tasks = agent.performance.success_count + agent.performance.failure_count
            if total_tasks == 1:
                agent.performance.avg_latency_sec = latency_sec
            else:
                # Exponential moving average
                agent.performance.avg_latency_sec = (
                    0.9 * agent.performance.avg_latency_sec + 0.1 * latency_sec
                )

        # Update last_active_at
        agent.last_active_at = datetime.now(UTC).isoformat()

        # Persist
        self.save_state()

    def list_candidates(
        self,
        role: Optional[str] = None,
        required_traits: Optional[Dict[str, Any]] = None,
        policy_context: Optional[Dict[str, Any]] = None,
    ) -> List[AgentInfo]:
        """
        Get viable candidates for routing.
        Per REGISTRY.md Section 5.3
        """
        candidates = []

        # Filter by status (only active)
        for agent_info in self.agents.values():
            if agent_info.status != "active":
                continue

            # Filter by role
            if role and agent_info.role != role:
                continue

            # Filter by required traits
            if required_traits:
                if not all(
                    agent_info.traits.get(key) == value for key, value in required_traits.items()
                ):
                    continue

            # Filter by policy context
            if policy_context:
                if not self._check_policy_compatibility(agent_info, policy_context):
                    continue

            candidates.append(agent_info)

        return candidates

    def _check_policy_compatibility(self, agent: AgentInfo, policy_context: Dict[str, Any]) -> bool:
        """Check if agent is compatible with policy context."""
        # Network restrictions
        if not policy_context.get("network_allowed", True):
            if agent.safety_profile.needs_network:
                return False

        # Sensitivity requirements
        sensitivity = policy_context.get("sensitivity", "low")
        if sensitivity == "high":
            # For high sensitivity, prefer agents with less external network access
            if (
                agent.safety_profile.needs_network
                and agent.safety_profile.irreversible_ops_possible
            ):
                return False

        return True

    def quarantine(self, agent_id: str, reason: str, society_memory=None) -> None:
        """
        Quarantine an agent due to policy violations or risky behavior.
        Per REGISTRY.md Section 5.4
        """
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        agent.status = "quarantined"
        agent.alive = True  # Still alive, just not routing

        # Persist
        self.save_state()

        # Log to society memory
        if society_memory:
            society_memory.add_entry(f"Quarantined {agent_id}: {reason}")

    def retire(self, agent_id: str, reason: str, society_memory=None) -> None:
        """
        Retire an agent that is underperforming or obsolete.
        Per REGISTRY.md Section 5.5
        """
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        agent.status = "retired"
        agent.alive = False
        agent.retired_at = datetime.now(UTC).isoformat()
        agent.retire_reason = reason

        # Persist
        self.save_state()

        # Log to society memory
        if society_memory:
            society_memory.add_entry(f"Retired {agent_id}: {reason}")

        # Write to agent's memory (if path exists)
        self._write_retirement_memory(agent, reason)

    def _write_retirement_memory(self, agent: AgentInfo, reason: str):
        """Write retirement notice to agent's memory file."""
        try:
            memory_dir = Path("memory/agents") / agent.agent_id
            memory_dir.mkdir(parents=True, exist_ok=True)

            today = datetime.now(UTC).strftime("%Y-%m-%d")
            memory_file = memory_dir / f"{today}.md"

            entry = f"""
## [{datetime.now(UTC).isoformat()}] RETIREMENT

- I am {agent.agent_id}.
- Reason for retirement: {reason}

"""

            with open(memory_file, "a") as f:
                f.write(entry)
        except Exception as e:
            print(f"Could not write retirement memory for {agent.agent_id}: {e}")

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """
        Get full metadata for one replica.
        Per REGISTRY.md Section 5.6
        """
        return self.agents.get(agent_id)

    # === Helper Methods ===

    def get_agents(self) -> Dict[str, AgentInfo]:
        """Get all registered agents."""
        return self.agents.copy()

    def get_agents_by_role(self, role: str) -> List[str]:
        """Get all agent IDs for a given role."""
        return self.roles.get(role, []).copy()

    def get_best_replica(self, role: str) -> Optional[str]:
        """Get the best performing replica for a role."""
        candidates = self.list_candidates(role=role)
        if not candidates:
            return None

        best_agent = max(candidates, key=lambda a: a.performance.avg_reward)
        return best_agent.agent_id

    def all_active_roles(self) -> List[str]:
        """Get all roles that have at least one active replica."""
        active_roles = set()
        for agent in self.agents.values():
            if agent.status == "active":
                active_roles.add(agent.role)
        return sorted(active_roles)

    def all_active_replicas(self, role: str) -> List[AgentInfo]:
        """Get all active replicas for a role."""
        return self.list_candidates(role=role)

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get overall registry statistics."""
        total_agents = len(self.agents)
        active = sum(1 for a in self.agents.values() if a.status == "active")
        quarantined = sum(1 for a in self.agents.values() if a.status == "quarantined")
        retired = sum(1 for a in self.agents.values() if a.status == "retired")

        return {
            "total_agents": total_agents,
            "active": active,
            "quarantined": quarantined,
            "retired": retired,
            "roles": len(self.roles),
            "unique_roles": self.all_active_roles(),
        }

    # === Dynamic Agent Registration (Phase 2) ===

    def register_dynamic_agent(self, manifest: Dict[str, Any]) -> None:
        """
        Register a dynamically generated agent scaffold in the registry with provenance.

        This does not auto-activate the agent; caller must decide status.
        """
        agent_name = manifest.get("agent_name")
        if not agent_name:
            raise ValueError("manifest.agent_name is required")

        # Minimal placeholder entry; real traits/capabilities will be filled when loaded
        info = AgentInfo(
            agent_id=agent_name,
            role=agent_name.replace("Agent", "Agent"),
            traits={"generated": True},
            instinct_paths=[],
            status="quarantined",  # default staged state
            alive=False,
            capabilities_summary=f"Generated scaffold from manifest {manifest.get('spec_path','')}.",
        )
        self.agents[agent_name] = info
        self.roles.setdefault(info.role, []).append(agent_name)
        self.save_state()

    def activate_agent(self, agent_id: str) -> bool:
        """Activate a previously registered (quarantined) dynamic agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        agent.status = "active"
        agent.alive = True
        # Ensure role index contains this agent
        self.roles.setdefault(agent.role, [])
        if agent_id not in self.roles[agent.role]:
            self.roles[agent.role].append(agent_id)
        self.save_state()
        return True
