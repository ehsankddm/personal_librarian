# Phase 2 — Progress Summary (vs current HEAD)

## Overview
Phase 2 brought the LLM into the loop and added a safe, explicit path for code generation, loading, and activation of new agents. The system remains deterministic by default with strong fallbacks and records all communications and model calls for audit.

## Key Additions
- LLM Gateway Client: `core/llm_client.py` (async, OpenAI-compatible; JSON parsing + redaction).
- Planner LLM decision: `PlannerAgent.reason_with_llm()` prints chosen route, justification, confidence.
- Gatekeeper advisory: non‑binding LLM rationale via the gateway.
- CodeGen scaffolds: `CodeGeneratorAgent` drafts spec and renders scaffold + MANIFEST (no auto‑exec).
- Loader: `AgentLoader.load_dynamic_agent()` for sandboxed class import.
- Registry: `register_dynamic_agent()` + `activate_agent()` to track provenance and status.
- Telemetry: persisted LLM events; added durable `messages` table to record every publish/dispatch.

## Explicit Approvals (User‑Driven)
- Approve load: type “approve load [agents/dynamic/Name/MANIFEST.json]”
  - Gatekeeper approves → Loader imports → Registry registers (quarantined).
- Activate agent: type “activate agent <AgentName>”
  - Gatekeeper approves → instantiate + subscribe to MessageBus → Registry status = active.

## Dev UX
- Interactive CLI is default; Phase 2 demo toggled with `PHASE2_DEV=1`.
- Phase 2 prints LLM decision and a one‑time Gatekeeper advisory.

## Safety & Persistence
- No side effects without Gatekeeper approval.
- All bus messages are persisted to `state/telemetry.db` (table `messages`).
- Telemetry captures prompts/responses with redaction; memory/logs continue to persist.

## How to Demo
- Run: `PHASE2_DEV=1 uv run --extra dev python run_dev.py`
- Trigger missing capability (e.g., ingestion). After scaffold is created:
  - Approve load: “approve load” (or with manifest path)
  - Activate: “activate agent GeneratedAgent_v1”

## Files Changed (diff vs HEAD)
```
Tracked changes:
actions/action_request.py
agents/agent_core.py
agents/code_generator_agent.py
agents/gatekeeper_agent.py
agents/planner_agent.py
core/bus.py
core/gatekeeper.py
core/loader.py
core/message.py
core/planner.py
core/registry.py
learning/telemetry_collector.py
memory/archive.py
memory/memory_log.py
memory/recall.py
memory/society_memory.py
pyproject.toml
run_dev.py

New/untracked:
core/llm_client.py
AGENTS.md
tests/test_gatekeeper_async.py
tests/test_message_bus_async.py
tests/test_planner_async.py
```

