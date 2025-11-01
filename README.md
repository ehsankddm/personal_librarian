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

## 🏗️ Architecture

Built on principles of:
- Language-based coordination
- Dynamic evolution
- Preference learning
- Safety constitution
- Transparency & explainability

## 📝 License

MIT License

