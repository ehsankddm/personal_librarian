"""Recall - Memory retrieval and search functionality."""

from typing import List, Dict, Any
from pathlib import Path
from memory.memory_log import MemoryLog


class Recall:
    """Provides memory recall and search capabilities."""

    def __init__(self, memory_log: MemoryLog):
        self.memory_log = memory_log

    def recall_recent_memory(self, agent_id: str, max_items: int = 10) -> List[str]:
        """
        Retrieve recent memory snippets for an agent.

        Per PHASE_1_ROADMAP §2: returns human-readable snippets with timestamps,
        capping length to avoid gigantic blobs.

        Args:
            agent_id: Agent to retrieve memories for
            max_items: Maximum number of recent log entries to return

        Returns:
            List of recent memory snippets (lines from log files)
        """
        agent_dir = self.memory_log.base_path / "agents" / agent_id

        if not agent_dir.exists():
            return []

        # Get today's log file
        from datetime import datetime, UTC

        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = agent_dir / f"{today_str}.md"

        if not log_file.exists():
            return []

        # Read log and split into recent entries
        content = log_file.read_text()

        # Split by "## " timestamps to get individual entries
        entries = content.split("## ")[1:]  # Skip first empty split

        snippets = []
        for entry in entries[-max_items:]:  # Last N entries
            # Limit entry length to reasonable size
            lines = entry.strip().split("\n")
            # Take first 10 lines max, truncate long ones
            truncated = []
            for line in lines[:10]:
                if len(line) > 150:
                    truncated.append(line[:147] + "...")
                else:
                    truncated.append(line)
            snippets.append("## " + "\n".join(truncated))

        return snippets

    def search(self, query: str, agent_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search through memories."""
        # TODO: Implement semantic search over memories
        # For now, simple text matching
        results = []

        if agent_id:
            recent_logs = self.memory_log.get_recent_logs(agent_id, days=30)
            for log in recent_logs:
                if query.lower() in log.lower():
                    results.append(
                        {
                            "agent_id": agent_id,
                            "content": log,
                            "relevance": 0.5,  # TODO: Calculate actual relevance
                        }
                    )
        else:
            # Search all agents
            agents_dir = self.memory_log.base_path / "agents"
            if agents_dir.exists():
                for agent_dir in agents_dir.iterdir():
                    if agent_dir.is_dir():
                        recent_logs = self.memory_log.get_recent_logs(agent_dir.name, days=30)
                        for log in recent_logs:
                            if query.lower() in log.lower():
                                results.append(
                                    {"agent_id": agent_dir.name, "content": log, "relevance": 0.5}
                                )

        return results[:limit]

    def get_context(self, agent_id: str, topic: str) -> str:
        """Retrieve relevant context for a topic."""
        results = self.search(topic, agent_id=agent_id, limit=5)
        context_parts = [r["content"] for r in results]
        return "\n\n---\n\n".join(context_parts)
