"""Recall - Memory retrieval and search functionality."""

from typing import List, Dict, Any
from pathlib import Path
from memory.memory_log import MemoryLog


class Recall:
    """Provides memory recall and search capabilities."""
    
    def __init__(self, memory_log: MemoryLog):
        self.memory_log = memory_log
    
    def search(self, query: str, agent_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search through memories."""
        # TODO: Implement semantic search over memories
        # For now, simple text matching
        results = []
        
        if agent_id:
            recent_logs = self.memory_log.get_recent_logs(agent_id, days=30)
            for log in recent_logs:
                if query.lower() in log.lower():
                    results.append({
                        'agent_id': agent_id,
                        'content': log,
                        'relevance': 0.5  # TODO: Calculate actual relevance
                    })
        else:
            # Search all agents
            agents_dir = self.memory_log.base_path / "agents"
            if agents_dir.exists():
                for agent_dir in agents_dir.iterdir():
                    if agent_dir.is_dir():
                        recent_logs = self.memory_log.get_recent_logs(agent_dir.name, days=30)
                        for log in recent_logs:
                            if query.lower() in log.lower():
                                results.append({
                                    'agent_id': agent_dir.name,
                                    'content': log,
                                    'relevance': 0.5
                                })
        
        return results[:limit]
    
    def get_context(self, agent_id: str, topic: str) -> str:
        """Retrieve relevant context for a topic."""
        results = self.search(topic, agent_id=agent_id, limit=5)
        context_parts = [r['content'] for r in results]
        return "\n\n---\n\n".join(context_parts)

