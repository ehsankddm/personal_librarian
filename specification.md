# 📚 Evolving Personal Librarian — Project Specification

---

## 🧭 Vision

A self-improving digital librarian that **learns**, **adapts**, and **extends itself** over time.

The system:
- Collects books automatically from multiple sources (Android downloads, Google Drive).
- Organizes and catalogs them locally and on an encrypted backup (Google Drive, NAS).
- Uses local LLMs to analyze, summarize, and tag books.
- Provides a natural language interface to browse, search, and download books.
- Evolves its own capabilities through agentic self-modification and safe code generation.
- Learns user preferences and adapts behaviors accordingly.
- Operates safely and within resource limits (privacy, cost, compute, etc.).

Ultimately, it becomes a **living librarian society** — a collection of cooperating agents that grow smarter over time.

---

## 🎯 Core Goals

| Category | Goal |
|-----------|------|
| **Automation** | Automatically import and organize new books from Android and Google Drive. |
| **Knowledge** | Generate granular metadata, summaries, semantic tags, and author info. |
| **Search** | Enable full-text and semantic RAG search over owned books. |
| **Interface** | Provide a chat-first interface, with dynamically generated forms and controls. |
| **Evolution** | Create new agents and features dynamically through controlled code generation. |
| **Learning** | Continuously learn from feedback, success, and failure via telemetry. |
| **Safety** | Protect privacy, data, and hardware; enforce cost and harm boundaries. |
| **Transparency** | Keep full English-language conversation logs and Markdown memories. |
| **Self-awareness** | Record reflections and improve instincts, preferences, and policies over time. |

---

## 🧬 Conceptual Overview

The system is a **multi-agent society**.

Each agent:
- Communicates in English.
- Has a role (e.g., BackupAgent, EnrichmentAgent).
- Possesses *instincts* (Markdown prompt priors), *preferences*, *policies*, and *memory*.
- Emits telemetry and learns from feedback.

The society includes:
- A **Planner** to coordinate and route tasks.
- A **Gatekeeper** to enforce cost/safety policies.
- A **Curator** to tune preferences and policies.
- A **Code Generator** to create new agents.
- A **Reflection Agent** to summarize and evolve instincts.
- Replicas (multiple versions of the same agent role) to explore strategies in parallel.

---

## 🧠 Core Architectural Principles

| Principle | Description |
|------------|--------------|
| **Language-based coordination** | Agents communicate in English messages over a shared message bus. |
| **Dynamic evolution** | New agents can be generated safely at runtime from textual specifications. |
| **Preference learning** | System learns user likes/dislikes and adapts style, verbosity, and priorities. |
| **Policy learning** | Planner learns which strategies and replicas perform best in context. |
| **Telemetry-driven feedback** | Every message, success, or failure produces structured telemetry. |
| **Markdown memory** | Each agent and the society itself maintain Markdown diaries with timestamps. |
| **Safety constitution** | A society-wide values file enforces non-destructive, cost-aware, private operation. |
| **Replicated agents** | Multiple variants of the same agent compete and evolve. |
| **Sandboxed execution** | All code and actions are gated and capability-limited. |
| **Transparency & explainability** | Every step, success, and failure is human-readable and versioned. |

---

## ⚙️ Functional Design

### 1. Agents

Each agent is a subclass of a shared `Agent` base class.

**Attributes:**
- `name`, `role`, `agent_id`
- `traits`: strategies or prompt variants
- `preferences`, `policies`, `instincts`
- `memory`: Markdown diary

**Behavior:**
- `can_handle(message)` → bool  
- `handle(message)` → English reply + telemetry  
- `speak()` → publish message on bus  
- `reward(success, magnitude)` → record reward  

**Responsibilities:**
- interpret natural language messages
- update or request tasks
- escalate if uncertain or stuck

---

### 2. Core Components

| Component | Purpose |
|------------|----------|
| **Message Bus** | Shared async queue for all communications. |
| **Planner** | Routes messages and tasks to appropriate agents or replicas. |
| **Registry** | Keeps list of all active agents, replicas, traits, and performance stats. |
| **Gatekeeper** | Validates all real-world actions (network, file writes, uploads). |
| **Curator** | Reads telemetry and updates preferences/policies. |
| **Code Generator** | Generates new agents dynamically using safe templates. |
| **Reflection Agent** | Summarizes memories and evolves instincts. |
| **Interface Agent** | Handles user chat, feedback, and escalation requests. |

---

### 3. Learning & Memory

**Telemetry & Reward Loop**
- Every action logs telemetry (success, cost, safety, escalation).
- RewardEngine converts telemetry into scalar rewards.
- PolicyLearner and PreferenceLearner adjust decision weights.

**Markdown Memories**
- `/memory/agents/<agent_id>/<YYYY-MM-DD>.md` — per-replica diaries.  
- `/memory/society/<YYYY-MM-DD>.md` — daily summaries.  
- Append-only, timestamped, human-readable.  

**Reflection**
- ReflectionAgent summarizes experiences and updates instincts.

---

### 4. Safety & Governance

| Layer | Mechanism | Enforced By |
|--------|------------|--------------|
| **Values** | `instincts/society_values.md` defines do-no-harm principles. | All agents |
| **Policies** | `state/policies.json` sets hard technical rules (network, cost, compute). | Gatekeeper |
| **Gatekeeper** | Executes only approved `ActionRequest`s. | Runtime |
| **Reward shaping** | Unsafe or costly behavior is penalized. | Learning loop |

---

### 5. Instincts & Behavior DNA

Instincts are Markdown prompt templates that encode behavior and ethics.

Examples:
- `instincts/default_agent_instinct.md`:  
  "If I’m stuck, escalate politely and log the situation."
- `instincts/society_values.md`:  
  "Protect user privacy and respect cost."
- `instincts/planner_instinct.md`:  
  "Coordinate, not dominate. When missing capability, spawn help."

They serve as stable behavioral priors.  
Policies and preferences are learned layers on top.

---

### 6. Replicas and Evolution

Each agent role can have multiple **replicas**:
- Different traits or instincts.
- Compete and cooperate to perform tasks.
- Tracked and scored individually by the RewardEngine.
- Underperformers are retired, top performers replicated.
- Planner routes tasks to the best-performing replica per context.

Evolution = safe experimentation.

---

## 🧩 Minimal Viable Society (MVS)

On boot, the system starts with:
- `Planner`
- `Gatekeeper`
- `Curator`
- `CodeGenerator`
- `InterfaceAgent`
- `MessageBus`, `Telemetry`, `Memory`, and the Constitution (instincts + policies)

No domain-specific agents are pre-coded.

When you issue a task like “Import my books from Drive,”  
the system:
1. Realizes no such agent exists.
2. Planner drafts a spec.
3. CodeGenerator creates an `IngestionAgent`.
4. Gatekeeper enforces safe execution.
5. Curator monitors results and updates learning.

---

## 🧱 Project Directory Structure

```text
personal-librarian/
├─ README.md
├─ pyproject.toml
├─ run_dev.py
│
├─ /core/
│   ├─ bus.py
│   ├─ message.py
│   ├─ planner.py
│   ├─ gatekeeper.py
│   ├─ registry.py
│   ├─ loader.py
│   ├─ sandbox.py
│   ├─ policies.py
│   ├─ preferences.py
│   └─ state_broadcast.py
│
├─ /agents/
│   ├─ agent_core.py
│   ├─ base_instinct_adapter.py
│   ├─ interface_agent.py
│   ├─ planner_agent.py
│   ├─ curator_agent.py
│   ├─ code_generator_agent.py
│   ├─ reflection_agent.py
│   ├─ gatekeeper_agent.py
│   ├─ /dynamic/
│   └─ /archetypes/
│
├─ /learning/
│   ├─ telemetry_collector.py
│   ├─ reward_engine.py
│   ├─ preference_learner.py
│   ├─ policy_learner.py
│   ├─ router_learner.py
│   └─ evaluator.py
│
├─ /memory/
│   ├─ memory_log.py
│   ├─ recall.py
│   ├─ society_memory.py
│   └─ archive.py
│
├─ /state/
│   ├─ preferences.json
│   ├─ policies.json
│   ├─ registry_state.json
│   └─ telemetry.db
│
├─ /instincts/
│   ├─ society_values.md
│   ├─ default_agent_instinct.md
│   ├─ planner_instinct.md
│   ├─ curator_instinct.md
│   ├─ code_generator_instinct.md
│   └─ gatekeeper_instinct.md
│
├─ /ui/
│   ├─ api_server.py
│   ├─ frontend/
│   └─ ui_config.json
│
├─ /actions/
│   ├─ action_request.py
│   ├─ executor.py
│   └─ cost_estimator.py
│
├─ /books/
│   ├─ by-id/
│   ├─ metadata_exports/
│   └─ encrypted_backup/
│
├─ /agents_generated_specs/
│   ├─ requested_capabilities/
│   ├─ drafts/
│   └─ accepted/
│
├─ /logs/
│   ├─ runtime.log
│   ├─ gatekeeper.log
│   └─ audit_actions.log
│
└─ /memory/
    ├─ agents/
    ├─ society/
    └─ archives/


🔐 Safety & Cost Enforcement

Layers of protection:

instincts/society_values.md — moral rules (no harm, no data leaks, no expensive operations).

state/policies.json — hard constraints (network allowlist, compute caps, encryption requirements).

Gatekeeper — only executes approved ActionRequests; asks user for permission if risky.

RewardEngine — penalizes costly or unsafe behaviors; rewards safe and efficient performance.

Telemetry — logs every action for auditability.


📈 Learning & Adaptation Lifecycle

Experience

Agents act, log telemetry, append to memory.

Feedback

User reactions and success rates generate rewards.

Learning

PreferenceLearner and PolicyLearner update behavior.

Evolution

Curator decides to spawn, modify, or retire replicas.

Reflection

ReflectionAgent summarizes insights and updates instincts.