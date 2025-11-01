"""Registry - Keeps track of all agents and their status."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentInfo:
    """Information about an agent."""
    agent_id: str
    role: str
    name: str
    status: str  # active, paused, stopped
    created_at: datetime = field(default_factory=datetime.now)
    traits: List[str] = field(default_factory=list)
    replica_id: Optional[str] = None
    performance_stats: Dict[str, float] = field(default_factory=dict)


class Registry:
    """Central registry of all agents."""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.roles: Dict[str, List[str]] = {}  # role -> [agent_ids]
    
    def register(self, agent_id: str, role: str, name: str, traits: List[str] = None, replica_id: str = None):
        """Register a new agent."""
        agent_info = AgentInfo(
            agent_id=agent_id,
            role=role,
            name=name,
            status="active",
            traits=traits or [],
            replica_id=replica_id
        )
        self.agents[agent_id] = agent_info
        
        # Track by role
        if role not in self.roles:
            self.roles[role] = []
        self.roles[role].append(agent_id)
    
    def unregister(self, agent_id: str):
        """Unregister an agent."""
        if agent_id in self.agents:
            agent_info = self.agents[agent_id]
            # Remove from role index
            if agent_info.role in self.roles:
                self.roles[agent_info.role].remove(agent_id)
            
            del self.agents[agent_id]
    
    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information."""
        return self.agents.get(agent_id)
    
    def get_agents(self) -> Dict[str, AgentInfo]:
        """Get all registered agents."""
        return self.agents.copy()
    
    def get_agents_by_role(self, role: str) -> List[str]:
        """Get all agent IDs for a given role."""
        return self.roles.get(role, []).copy()
    
    def update_performance(self, agent_id: str, stats: Dict[str, float]):
        """Update performance statistics for an agent."""
        if agent_id in self.agents:
            self.agents[agent_id].performance_stats.update(stats)
    
    def get_best_replica(self, role: str) -> Optional[str]:
        """Get the best performing replica for a role."""
        candidates = self.get_agents_by_role(role)
        if not candidates:
            return None
        
        best_score = -1
        best_agent = None
        
        for agent_id in candidates:
            stats = self.agents[agent_id].performance_stats
            score = stats.get('reward', 0)
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent

