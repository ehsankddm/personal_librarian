"""Loader - Dynamic agent loading and initialization."""

import importlib
import importlib.util
from pathlib import Path
from typing import Type, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.agent_core import Agent


class AgentLoader:
    """Loads and instantiates agents dynamically."""
    
    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.loaded_modules: Dict[str, Any] = {}
    
    def load_agent_class(self, module_path: str, class_name: str) -> Type['Agent']:
        """Load an agent class from a module."""
        if module_path not in self.loaded_modules:
            spec = importlib.util.spec_from_file_location(
                class_name.lower(),
                self.agents_dir / module_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.loaded_modules[module_path] = module
        
        module = self.loaded_modules[module_path]
        return getattr(module, class_name)
    
    def create_agent_instance(
        self,
        agent_id: str,
        role: str,
        agent_class: Type['Agent'],
        **kwargs
    ) -> 'Agent':
        """Create an agent instance."""
        return agent_class(agent_id=agent_id, role=role, **kwargs)
    
    def load_from_generated(self, agent_spec_path: str) -> 'Agent':
        """Load an agent from a generated specification."""
        # TODO: Implement generation-based loading
        pass

