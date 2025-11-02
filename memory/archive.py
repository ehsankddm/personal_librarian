"""Archive - Archives old memories for long-term storage."""

from pathlib import Path
from datetime import datetime, timedelta
import shutil


class Archive:
    """Manages archival of old memories."""

    def __init__(self, base_path: str = "memory", archive_path: str = "memory/archives"):
        self.base_path = Path(base_path)
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)

    def archive_old_memories(self, days_threshold: int = 90):
        """Archive memories older than threshold."""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        # Archive society memories
        society_dir = self.base_path / "society"
        if society_dir.exists():
            for file in society_dir.glob("*.md"):
                file_date = datetime.fromtimestamp(file.stat().st_mtime)
                if file_date < cutoff_date:
                    archive_path = self.archive_path / "society" / file.name
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file), str(archive_path))

        # Archive agent memories
        agents_dir = self.base_path / "agents"
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if agent_dir.is_dir():
                    for file in agent_dir.glob("*.md"):
                        file_date = datetime.fromtimestamp(file.stat().st_mtime)
                        if file_date < cutoff_date:
                            archive_path = self.archive_path / "agents" / agent_dir.name / file.name
                            archive_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(file), str(archive_path))
