# 📚 Evolving Personal Librarian

A self-improving digital librarian that learns, adapts, and extends itself over time.

## 🧭 Vision

The Personal Librarian is a multi-agent society designed to:
- Collect and organize books from multiple sources (Android, Google Drive, etc.)
- Analyze and catalog using local LLMs
- Provide natural language interface for browsing and searching
- Evolve its capabilities through safe code generation
- Learn user preferences and adapt behaviors

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for project management

### Development

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates virtual env if needed)
uv sync

# Or manually create venv and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run development server
python run_dev.py
```

### Core Components

- **Agents**: Multi-agent society coordinating tasks
- **Message Bus**: Async communication backbone
- **Gatekeeper**: Safety and policy enforcement
- **Curator**: Learning and adaptation
- **Code Generator**: Dynamic agent creation
- **Reflection Agent**: Continuous improvement

## 📖 Documentation

- `specification.md` - Detailed architecture and design
- `SETUP.md` - Setup and development guide
- `UV_USAGE.md` - Guide to using uv for project management
- `ROADMAP.md` - Development phases and milestones
- `PHASE_0_PROGRESS.md` - Agent skeleton implementation status
- `PHASE_0_ACTION_REQUEST.md` - ActionRequest system implementation
- `PHASE_0_PLANNER.md` - Planner and Message Bus implementation
- `PHASE_0_REGISTRY.md` - Registry and Replica Management

## 🧪 Phase 2 — LLM + Safe Codegen

- Demo: `PHASE2_DEV=1 uv run --extra dev python run_dev.py` (interactive CLI is default).
- LLM Gateway `.env` (loaded by `run_dev.py`):
  - `LLM_BASE=http://localhost:7766`
  - `LLM_API_KEY=your-key`
  - `LLM_MODEL_ALIAS=gpt-4o-mini`
- Missing capability → CodeGeneratorAgent writes:
  - Draft spec: `agents_generated_specs/drafts/*.md`
  - Scaffold + `MANIFEST.json`: `agents/dynamic/<AgentName>/`
- Approvals (type in CLI):
  - Approve load: `approve load [agents/dynamic/<AgentName>/MANIFEST.json]`
  - Activate agent: `activate agent <AgentName>`
  - Both actions are approved by Gatekeeper and logged.

## 🧷 Telemetry & Message Persistence

- Logs:
  - Runtime: `logs/runtime.log`
  - Gatekeeper audit: `logs/audit_actions.log`
- SQLite DB: `state/telemetry.db`
  - `telemetry` table: agent events (action, success, metadata)
  - `messages` table: every bus message (published and dispatched)

Query examples (last 10 minutes):

```bash
# Recent bus messages
sqlite3 state/telemetry.db \
  "SELECT id, stage, type, sender_id, receiver_id, timestamp, substr(content,1,200) AS content
   FROM messages WHERE created_at >= datetime('now','-10 minutes') ORDER BY id;"

# Recent telemetry events
sqlite3 state/telemetry.db \
  "SELECT id, agent_id, action, success, duration_ms, timestamp, substr(metadata,1,200) AS meta
   FROM telemetry WHERE created_at >= datetime('now','-10 minutes') ORDER BY id;"

# Totals
sqlite3 state/telemetry.db "SELECT COUNT(*) FROM messages;"
```

Notes:
- Interactive CLI prints user messages; the bus log shows a short preview.
- LLM calls record `llm_prompt` and `llm_response` with redaction; CodeGen emits `codegen_spec_draft` and `codegen_scaffold_rendered`.

## 🏗️ Architecture

Built on principles of:
- Language-based coordination
- Dynamic evolution
- Preference learning
- Safety constitution
- Transparency & explainability

## 📝 License

MIT License
