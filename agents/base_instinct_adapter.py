"""Base instinct adapter - Helper for agents to work with instincts."""

from typing import Dict, Any
from pathlib import Path


class InstinctAdapter:
    """Adapter for loading and applying instincts."""

    def __init__(self, instincts_path: str):
        self.instincts_path = Path(instincts_path)
        self.instincts_text = self._load()

    def _load(self) -> str:
        """Load instincts from file."""
        if self.instincts_path.exists():
            return self.instincts_path.read_text()
        return ""

    def format(self, **context: Any) -> str:
        """
        Format instincts template with context variables.

        Example:
            instincts = "You are {role}. {guidance}"
            formatted = adapter.format(role="Assistant", guidance="Be helpful.")
        """
        try:
            return self.instincts_text.format(**context)
        except KeyError as e:
            return f"Instinct formatting error: {e}"

    def get_guidelines(self) -> list[str]:
        """Extract bullet points or guidelines from instincts."""
        lines = self.instincts_text.split("\n")
        guidelines = []
        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                guidelines.append(line[2:])
        return guidelines

    def reload(self):
        """Reload instincts from disk."""
        self.instincts_text = self._load()
