"""Memory Log - Manages agent memory diaries."""

from pathlib import Path
from datetime import datetime
from typing import List, Optional


class MemoryLog:
    """Manages markdown memory logs for agents."""

    def __init__(self, base_path: str = "memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def log_entry(self, agent_id: str, entry: str, timestamp: datetime = None):
        """Append an entry to an agent's memory log."""
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime("%Y-%m-%d")
        agent_dir = self.base_path / "agents" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        log_file = agent_dir / f"{date_str}.md"

        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        formatted_entry = f"\n## {timestamp_str}\n\n{entry}\n"

        with open(log_file, "a") as f:
            f.write(formatted_entry)

    def get_log(self, agent_id: str, date: datetime = None) -> str:
        """Retrieve an agent's memory log for a specific date."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        log_file = self.base_path / "agents" / agent_id / f"{date_str}.md"

        if log_file.exists():
            return log_file.read_text()
        return ""

    def get_recent_logs(self, agent_id: str, days: int = 7) -> List[str]:
        """Get recent memory logs for an agent."""
        logs = []
        agent_dir = self.base_path / "agents" / agent_id

        if not agent_dir.exists():
            return logs

        # Get all log files sorted by date
        log_files = sorted(agent_dir.glob("*.md"), reverse=True)[:days]

        for log_file in log_files:
            logs.append(log_file.read_text())

        return logs
