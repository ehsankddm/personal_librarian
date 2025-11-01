"""Preferences - User preferences and learned adaptations per specifications."""

from typing import Dict, Any
import json
from pathlib import Path


class PreferenceManager:
    """Manages preferences from state/preferences.json."""
    
    def __init__(self, preferences_path: str = "state/preferences.json"):
        self.preferences_path = Path(preferences_path)
        self.preferences: Dict[str, Any] = {}
        self.load_from_file()
    
    def load_from_file(self):
        """Load preferences from JSON file."""
        if not self.preferences_path.exists():
            # Use defaults if file doesn't exist
            self._load_defaults()
            return
        
        with open(self.preferences_path, 'r') as f:
            self.preferences = json.load(f)
    
    def _load_defaults(self):
        """Load default preferences."""
        self.preferences = {
            "communication.verbosity": "normal",
            "communication.style": "neutral",
            "summary.style": "short_bullets",
            "max_retries": 3,
            "confirmation.require_before_send_to_kindle": True,
            "confirmation.require_before_delete": True
        }
        self.save_to_file()
    
    def save_to_file(self):
        """Save preferences to JSON file."""
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.preferences_path, 'w') as f:
            json.dump(self.preferences, f, indent=2)
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self.preferences.get(path, default)
    
    def set(self, path: str, value: Any):
        """Set a preference value."""
        self.preferences[path] = value
        self.save_to_file()
    
    def get_preference(self, path: str, default: Any = None) -> Any:
        """Alias for get() for AGENT.md compliance."""
        return self.get(path, default)
    
    def update_from_feedback(self, feedback: Dict[str, Any]):
        """Update preferences based on user feedback."""
        # TODO: Implement preference learning from feedback
        # CuratorAgent will call this
        pass
