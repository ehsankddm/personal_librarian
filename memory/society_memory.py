"""Society Memory - Manages society-level memory summaries."""

from pathlib import Path
from datetime import datetime
from typing import Optional


class SocietyMemory:
    """Manages society-level memory summaries."""

    def __init__(self, base_path: str = "memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.society_dir = self.base_path / "society"
        self.society_dir.mkdir(parents=True, exist_ok=True)

    def add_entry(self, entry: str, timestamp: datetime = None):
        """Add an entry to the society memory."""
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime("%Y-%m-%d")
        log_file = self.society_dir / f"{date_str}.md"

        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        formatted_entry = f"\n## {timestamp_str}\n\n{entry}\n"

        with open(log_file, "a") as f:
            f.write(formatted_entry)

    def get_entry(self, date: datetime = None) -> str:
        """Get society memory for a specific date."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        log_file = self.society_dir / f"{date_str}.md"

        if log_file.exists():
            return log_file.read_text()
        return ""
