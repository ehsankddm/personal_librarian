"""Preferences - User preferences and learned adaptations."""

from typing import Dict, Any
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class Preferences:
    """User and system preferences."""
    verbosity_level: str = "normal"  # minimal, normal, verbose
    response_style: str = "professional"  # casual, professional, technical
    auto_actions: bool = False
    safety_tolerance: float = 0.5
    custom_preferences: Dict[str, Any] = field(default_factory=dict)


class PreferenceManager:
    """Manages preferences and learned adaptations."""
    
    def __init__(self, preferences_path: str = "state/preferences.json"):
        self.preferences_path = Path(preferences_path)
        self.preferences = Preferences()
        self.load_from_file()
    
    def load_from_file(self):
        """Load preferences from JSON file."""
        if self.preferences_path.exists():
            with open(self.preferences_path, 'r') as f:
                data = json.load(f)
                self.preferences = Preferences(**data)
    
    def save_to_file(self):
        """Save preferences to JSON file."""
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'verbosity_level': self.preferences.verbosity_level,
            'response_style': self.preferences.response_style,
            'auto_actions': self.preferences.auto_actions,
            'safety_tolerance': self.preferences.safety_tolerance,
            'custom_preferences': self.preferences.custom_preferences
        }
        
        with open(self.preferences_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return getattr(self.preferences, key, default)
    
    def set(self, key: str, value: Any):
        """Set a preference value."""
        if hasattr(self.preferences, key):
            setattr(self.preferences, key, value)
            self.save_to_file()
        else:
            self.preferences.custom_preferences[key] = value
            self.save_to_file()
    
    def update_from_feedback(self, feedback: Dict[str, Any]):
        """Update preferences based on user feedback."""
        # TODO: Implement preference learning from feedback
        pass

