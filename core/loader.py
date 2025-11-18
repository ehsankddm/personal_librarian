"""Loader - Dynamic agent loading and initialization."""

import importlib
import importlib.util
from pathlib import Path
from typing import Type, Dict, Any, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from agents.agent_core import Agent


class AgentLoader:
    """Loads and instantiates agents dynamically."""

    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.loaded_modules: Dict[str, Any] = {}

    def load_agent_class(self, module_path: str, class_name: str) -> Type["Agent"]:
        """Load an agent class from a module."""
        if module_path not in self.loaded_modules:
            spec = importlib.util.spec_from_file_location(
                class_name.lower(), self.agents_dir / module_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.loaded_modules[module_path] = module

        module = self.loaded_modules[module_path]
        return getattr(module, class_name)

    def create_agent_instance(
        self, agent_id: str, role: str, agent_class: Type["Agent"], **kwargs
    ) -> "Agent":
        """Create an agent instance."""
        return agent_class(agent_id=agent_id, role=role, **kwargs)

    def load_from_generated(self, agent_spec_path: str) -> "Agent":
        """Load an agent from a generated specification."""
        # TODO: Implement generation-based loading
        pass

    def load_dynamic_agent(self, manifest_path: str) -> Type["Agent"]:
        """
        Load a dynamically generated agent class from a manifest.

        Assumes scaffold layout created by CodeGeneratorAgent:
        agents/dynamic/<AgentName>/<agentname_lower>.py defines class <AgentName>.
        """
        mp = Path(manifest_path)
        manifest = json.loads(mp.read_text())
        agent_name = manifest["agent_name"]
        module_filename = f"{agent_name.lower()}.py"

        module_rel = Path("agents/dynamic") / agent_name / module_filename
        if not module_rel.exists():
            raise FileNotFoundError(f"Module not found: {module_rel}")

        return self.load_agent_class(str(module_rel), agent_name)
