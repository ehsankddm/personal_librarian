# Setup Guide

## Project Structure Created

The Personal Librarian project structure has been successfully created based on `specification.md`.

### Core Components

✅ **Core System** (`core/`)
- Message bus for agent communication
- Planner for coordination
- Gatekeeper for safety enforcement
- Registry for agent management
- Policy and preference managers
- Sandbox for safe code execution

✅ **Agents** (`agents/`)
- Agent base class
- Interface agent for user interaction
- Planner agent for coordination
- Curator agent for learning
- Code generator agent for dynamic agent creation
- Reflection agent for self-improvement
- Gatekeeper agent for policy enforcement

✅ **Learning System** (`learning/`)
- Telemetry collection
- Reward engine
- Preference learning
- Policy learning
- Router learning
- Performance evaluation

✅ **Memory System** (`memory/`)
- Agent memory logs
- Society memory summaries
- Recall/search functionality
- Archive management

✅ **Instincts** (`instincts/`)
- Society values constitution
- Default agent behavior
- Role-specific instincts

✅ **Actions** (`actions/`)
- Action request structure
- Executor for safe execution
- Cost estimation

✅ **UI** (`ui/`)
- API server framework
- Configuration

### Directory Structure

All directories from the specification have been created:
- `/core` - Core system components
- `/agents` - Agent implementations
- `/learning` - Learning and adaptation
- `/memory` - Memory management
- `/state` - Configuration and state
- `/instincts` - Behavior templates
- `/ui` - User interface
- `/actions` - Action management
- `/books` - Book storage
- `/agents_generated_specs` - Generated agent specs
- `/logs` - Log files
- `/memory` - Memory storage

## Next Steps

### 1. Install Dependencies

Using `uv` (recommended):
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates virtual env if needed)
uv sync

# Or manually create venv and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

Or using `pip`:
```bash
pip install -e .
```

### 2. Development

Most components have skeleton implementations with TODOs. Areas needing implementation:

**High Priority:**
- [ ] Complete agent message handling logic
- [ ] Implement code generation templates and sandboxing
- [ ] Build actual telemetry collection and reward calculation
- [ ] Create web UI with actual frontend
- [ ] Implement LLM integration for book analysis

**Medium Priority:**
- [ ] Add preference learning from feedback
- [ ] Implement policy tuning
- [ ] Build reflection and instinct evolution
- [ ] Create agent archetype templates
- [ ] Add semantic search for memories

**Lower Priority:**
- [ ] Add encryption for backups
- [ ] Implement NAS integration
- [ ] Add Android device integration
- [ ] Build advanced routing strategies

### 3. Testing

Run basic syntax check:
```bash
python -m py_compile core/*.py agents/*.py learning/*.py memory/*.py
```

### 4. Running

Start the development server:
```bash
python run_dev.py
```

Note: The current implementation is mostly skeletal. Most functionality needs to be completed per Phase 0 (Kernel) of the roadmap.

## Architecture Highlights

### Multi-Agent Society
- Agents communicate via message bus
- Each agent has instincts, preferences, and memory
- Replicas allow experimentation and evolution

### Safety First
- Gatekeeper enforces all actions
- Sandbox validates generated code
- Policies define hard boundaries

### Learning & Evolution
- Telemetry drives reward signals
- Preferences adapt to user feedback
- Reflection updates instincts
- Code generation creates new capabilities

### Transparency
- Markdown memory logs
- Human-readable communication
- Version-controlled instincts

## File Count

- **52 Python files** - Core implementation
- **6 Markdown files** - Instincts and documentation
- **3 JSON files** - Configuration
- **24 directories** - Organized structure

All files are ready for development!

