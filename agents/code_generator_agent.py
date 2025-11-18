"""Code Generator Agent - Creates new agents dynamically (scaffolds only in Phase 2)."""

from __future__ import annotations

import json
import re
import hashlib
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.message import Message, MessageType
from agents.agent_core import Agent
from core.sandbox import Sandbox


class CodeGeneratorAgent(Agent):
    """Agent responsible for generating new agents."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.generated_agents = []

    async def can_handle(self, message: Message) -> bool:
        """Handle agent creation requests."""
        if self.retired:
            return False

        return (
            "create agent" in message.content.lower()
            or "generate agent" in message.content.lower()
            or "new agent" in message.content.lower()
        )

    async def handle(self, message: Message) -> Optional[Message]:
        """Generate a scaffold for a new agent based on a request.

        Phase 2: Draft spec and render scaffold+manifest; do not auto-load.
        """
        content = message.content.lower()
        # Try to extract a spec path if provided by Planner
        spec_match = re.search(r"spec at ([^\s]+)", message.content)
        requested_spec_path = spec_match.group(1) if spec_match else None

        # Build a basic spec draft
        goal = message.content.strip()
        draft_path = self._write_spec_draft(goal, requested_spec_path)

        # Derive a conservative agent name from goal
        agent_name = self._derive_agent_name(goal)

        # Render a minimal scaffold and manifest
        manifest_path, files = await self._render_scaffold(agent_name, draft_path)

        # Telemetry events
        self.log_event(
            {
                "type": "codegen_spec_draft",
                "success": True,
                "path": str(draft_path),
            }
        )
        self.log_event(
            {
                "type": "codegen_scaffold_rendered",
                "success": True,
                "manifest": str(manifest_path),
                "files": [str(p) for p in files],
            }
        )

        response = (
            "Code generation (scaffold-only) complete.\n"
            f"Draft spec: {draft_path}\n"
            f"Manifest: {manifest_path}\n"
            "No dynamic load performed (requires explicit approval)."
        )

        # Also notify the user directly for visibility in interactive sessions
        await self.speak(
            content=response,
            recipient="user",
            message_type=MessageType.NOTIFICATION,
        )

        # Do not bounce a response back to Planner to avoid routing loops.
        # We already notified the user directly above.
        return None

    def describe_capabilities(self) -> str:
        """Describe what this agent can do."""
        return f"I am {self.agent_id}. I generate new agents dynamically from specifications."

    async def generate_agent_code(self, spec: dict) -> str:
        """Generate Python code for an agent from specification."""
        # TODO: Use template and spec to generate code
        pass

    async def validate_agent_code(self, code: str) -> tuple[bool, str]:
        """Validate generated code using sandbox."""
        # TODO: Implement sandbox validation
        return True, "Code validated successfully"

    # === Phase 2 helpers ===

    def _write_spec_draft(self, goal: str, requested_spec_path: Optional[str]) -> Path:
        drafts_dir = Path("agents_generated_specs/drafts")
        drafts_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        filename = f"draft_{ts}.md"
        draft_path = drafts_dir / filename

        body = f"""
# Agent Spec Draft

## Goal
{goal}

## Context
Requested by: {self.agent_id}
Requested at: {datetime.now(UTC).isoformat()}

## Constraints
- Phase 2 scaffold only (no auto-load)
- Must integrate with MessageBus and Registry
- Must route via Planner; safety via Gatekeeper

## Suggested Capabilities
- Handle ingestion-like tasks for Android downloads
- Report results and telemetry
- Request ActionRequests for any side effects

        """.strip()

        if requested_spec_path and Path(requested_spec_path).exists():
            body += f"\n\n## Reference\nOriginal request: {requested_spec_path}\n"

        draft_path.write_text(body)
        return draft_path

    def _derive_agent_name(self, goal: str) -> str:
        # Simple heuristic for Phase 2
        name = "GeneratedAgent"
        g = goal.lower()
        if "ingest" in g or "import" in g or "scan" in g:
            if "android" in g:
                name = "AndroidIngestionAgent"
            else:
                name = "IngestionAgent"
        elif "backup" in g:
            name = "BackupAgent"
        elif "metadata" in g or "enrich" in g or "tag" in g:
            name = "EnrichmentAgent"
        return f"{name}_v1"

    async def _render_scaffold(self, agent_name: str, spec_path: Path) -> tuple[Path, List[Path]]:
        dynamic_root = Path("agents/dynamic")
        dynamic_root.mkdir(parents=True, exist_ok=True)
        # Ensure packages exist
        (dynamic_root / "__init__.py").write_text("\n") if not (dynamic_root / "__init__.py").exists() else None

        base_dir = dynamic_root / agent_name
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "__init__.py").write_text("\n") if not (base_dir / "__init__.py").exists() else None

        # File contents
        class_name = agent_name
        module_name = f"{agent_name.lower()}"
        agent_py = base_dir / f"{module_name}.py"
        test_py = Path("tests_dynamic") / f"test_{module_name}.py"
        test_py.parent.mkdir(parents=True, exist_ok=True)

        agent_code = f"""
from typing import Optional
from agents.agent_core import Agent
from core.message import Message, MessageType


class {class_name}(Agent):
    async def can_handle(self, message: Message) -> bool:
        return False  # Placeholder in scaffold

    async def handle(self, message: Message) -> Optional[Message]:
        return None

    def describe_capabilities(self) -> str:
        return "Scaffold for {class_name} generated by {self.agent_id}"
""".lstrip()

        test_code = f"""
import pytest
from agents.dynamic.{agent_name}.{module_name} import {class_name}


def test_scaffold_imports():
    # Ensure class can be imported
    assert {class_name}
""".lstrip()

        # Write files
        agent_py.write_text(agent_code)
        test_py.write_text(test_code)

        # Compute hashes
        files = [agent_py, test_py]
        entries = []
        for p in files:
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            entries.append({"path": str(p), "sha256": sha, "mode": "text"})

        manifest = {
            "agent_name": agent_name,
            "files": entries,
            "spec_path": str(spec_path),
            "generated_by": self.agent_id,
            "created_at": datetime.now(UTC).isoformat(),
            "self_test_cmd": f"pytest -q {test_py}",
        }

        manifest_path = base_dir / "MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return manifest_path, files
