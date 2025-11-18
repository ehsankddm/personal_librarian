# PHASE 2 — LLM-in-the-Loop & Safe Code Generation (Roadmap)

> Phase 2 turns the Phase 1 context bundles into **real model calls** and enables **safe, deterministic code generation** for new capabilities. The system still favors safety, “dry-run first,” and explicit user approval for anything with side effects.

---

## 1) High-Level Objectives

1. **LLM in the loop:** Agents can call a local LLM using the Phase 1 context bundle contract and receive structured replies (plans, decisions, drafts).
2. **Safe tool/function calling:** Planner can ask the LLM to choose a route (from deterministic candidates). Gatekeeper can ask the LLM to draft an approval rationale (but Gatekeeper still makes the final decision deterministically).
3. **Code generation (scaffold only):** CodeGeneratorAgent can ask an LLM to draft *scaffolds/specs/stubs* for new agents (files under `agents_generated_specs/` and `agents/dynamic/`). **No auto-execution** without Gatekeeper approval.
4. **Dynamic loading (sandboxed):** Loader can import newly generated *scaffold* classes from `agents/dynamic/` **only after Gatekeeper approval** and Planner registration.
5. **Observability:** All model prompts, responses, tool calls, and approvals are captured in Telemetry with redaction options.
6. **Deterministic fallbacks:** If the model is unavailable or returns invalid output, the system falls back to Phase 1 deterministic behavior.

---

## 2) Scope (What changes in Phase 2)

### 2.1 Local LLM Client
- Add `core/llm_client.py` (or extend an existing module) with a **single interface**:
  - `generate_reasoning(context_bundle: dict, system_prompt: str, tools: list[ToolSpec] | None) -> LLMResult`
- Must support **at least one** local backend (choose one and mock others):
  - **Ollama** (preferred simple dev path) OR
  - **LM Studio** OR
  - **Local OpenAI-compatible server**
- Support **JSON mode** for structured outputs where relevant (plans, action choices).

### 2.2 Planner: LLM-Assisted Routing (Dry-Run)
- Add method: `PlannerAgent.reason_with_llm(bundle) -> RoutingDecision`
  - Input: Phase 1 `build_llm_context()` bundle + deterministic candidate routes and constraints.
  - Output (JSON): `{ "chosen_route": "...", "justification": "...", "confidence": 0–1, "needs_user_confirmation": bool }`
- **Dry-run** only in Phase 2: Planner still **does not** execute side effects; it proposes a route and, if risky, asks Gatekeeper/User.
- If LLM returns invalid JSON or unsafe suggestion, **fall back** to deterministic `plan_next_step()`.

### 2.3 Gatekeeper: LLM-Aided Rationale (Advisory Only)
- Add method: `GatekeeperAgent.advise_on(request: ActionRequest, bundle) -> Advisory`
  - Gatekeeper builds its safety bundle (as in Phase 1) and **optionally** asks LLM for a *rationale draft*.
  - Gatekeeper **still** decides deterministically (existing policy engine is authoritative).
  - Expected JSON output from LLM: `{ "risk_summary": "...", "policy_refs": ["..."], "suggested_decision": "approve|deny|escalate", "user_prompt": "..." }`
- If LLM response is missing or malformed → **ignore** and proceed deterministically.

### 2.4 CodeGeneratorAgent: Scaffolds Only
- Extend: `CodeGeneratorAgent.propose_agent_spec(task) -> AgentSpecDraft`
  - Ask LLM to produce Markdown spec first (saved under `agents_generated_specs/drafts/*.md`).
- Extend: `CodeGeneratorAgent.render_scaffold(spec) -> list[GeneratedFile]`
  - Render minimal, testable **scaffold** Python files into `agents/dynamic/<NewAgentName>/`.
  - Include unit test skeletons (`tests_dynamic/`) and a `MANIFEST.json` listing all generated files, hashes, and a self-test command.
- **No auto-enable:** The new agent is **not** loaded until:
  1) Gatekeeper approves the change, and
  2) `core/loader.py` loads and registers it, and
  3) Registry persists it.

### 2.5 Loader & Registry
- Loader: add `load_dynamic_agent(manifest_path)` that imports classes from `agents/dynamic/...` within a sandbox (restricted imports, no network).
- Registry: add `register_dynamic_agent(manifest)` with additional metadata (`generated_by`, `hashes`, `approved_by`, `loaded_at`).

### 2.6 Telemetry & Redaction
- Telemetry events to add:
  - `llm_prompt`, `llm_response`, `llm_validation_error`
  - `codegen_spec_draft`, `codegen_scaffold_rendered`
  - `dynamic_agent_loaded`, `dynamic_agent_rejected`
- Redact paths and PII when logging prompts/responses (basic regex redaction is fine in Phase 2).

### 2.7 InterfaceAgent Dev UX
- In dev mode, after a Planner decision, print:
  - “— LLM DECISION (Planner) —” with route, justification, and confidence.
  - When codegen requested: print path to the draft spec + scaffold manifest.

---

## 3) Safety Guarantees (Phase 2)

1. **No direct execution from LLM:** All side effects remain behind Gatekeeper + deterministic checks.
2. **Dry-run bias:** Planner uses LLM output as advice; final action requests still go through Gatekeeper.
3. **Human-in-the-loop for new code:** New agents must be approved by Gatekeeper (or the user) before loading.
4. **Logging & audit:** All prompts/responses and loader events are telemetered with redaction.
5. **Fallbacks:** If LLM fails, deterministic behavior continues as in Phase 1.
6. **Resource guardrails:** Enforce policy caps for model tokens/time/cost; deny or cut off long runs. (Even local models cost CPU/GPU.)

---

## 4) Interfaces & Types

### 4.1 LLM Client Types
```python
class LLMResult(TypedDict):
    raw_text: str
    parsed_json: dict | None
    finish_reason: str  # e.g., "stop", "length", "tool_call"
    tokens_in: int
    tokens_out: int
    model_name: str
    elapsed_ms: int
```
```python
def generate_reasoning(context_bundle: dict, system_prompt: str, tools: list[dict] | None) -> LLMResult: ...
```

### 4.2 Planner RoutingDecision
```python
class RoutingDecision(TypedDict):
    chosen_route: str
    justification: str
    confidence: float  # 0.0–1.0
    needs_user_confirmation: bool
```

### 4.3 Gatekeeper Advisory
```python
class Advisory(TypedDict):
    risk_summary: str
    policy_refs: list[str]
    suggested_decision: str  # "approve" | "deny" | "escalate"
    user_prompt: str
```

### 4.4 CodeGen Manifest
```python
class GeneratedFile(TypedDict):
    path: str
    sha256: str
    mode: str  # "text"
```
```python
class ScaffoldManifest(TypedDict):
    agent_name: str
    files: list[GeneratedFile]
    spec_path: str
    generated_by: str  # agent_id
    created_at: str
    self_test_cmd: str
```

---

## 5) Implementation Plan (Tasks)

1. **LLM Client**
   - [ ] Implement `core/llm_client.py` with a pluggable backend (start with a `MockLocalLLM` that returns deterministic JSON; later wire Ollama).
   - [ ] Add settings in `state/preferences.json` for model name, max tokens, and JSON mode.

2. **Planner (LLM Assisted)**
   - [ ] Add `reason_with_llm()` using `build_llm_context()` + deterministic candidates.
   - [ ] Validate and coerce LLM JSON; on failure, fallback to `plan_next_step()`.
   - [ ] In dev mode, print “— LLM DECISION (Planner) —” including confidence.

3. **Gatekeeper (Advisory)**
   - [ ] Add `advise_on()` that asks LLM for rationale draft; decision remains deterministic.
   - [ ] Telemetry: log prompt/response; redaction enabled.

4. **CodeGeneratorAgent**
   - [ ] Implement `propose_agent_spec()` → writes `agents_generated_specs/drafts/*.md`.
   - [ ] Implement `render_scaffold()` → writes code into `agents/dynamic/<AgentName>/` + `MANIFEST.json`.
   - [ ] Unit-test: confirm file list and hashes match `MANIFEST.json`.

5. **Loader & Registry**
   - [ ] Implement sandboxed `load_dynamic_agent(manifest_path)`.
   - [ ] Add `register_dynamic_agent()` + persistence.
   - [ ] Add Gatekeeper approval path for dynamic load.

6. **Telemetry**
   - [ ] Add new event types + redaction.
   - [ ] Add counters for model calls, token usage.

7. **Dev UX & run_dev.py**
   - [ ] Add a Phase 2 demo path (`PHASE2_DEV=1`): after Phase 1 output, call Planner’s LLM path, log the decision, then ask CodeGeneratorAgent to draft a scaffold (dry-run end).

---

## 6) Acceptance Tests (Dev Runs)

### 6.1 Planner LLM Decision (Dry-Run)
```
cd /Users/akira/projects/personal_librarian && rm -f state/registry_state.json state/telemetry.db && PHASE2_DEV=1 python3 -c "
import asyncio
from run_dev import main
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('\\nShutdown')
" 2>&1 | sed -n '1,160p'
```
**We expect to see:**
- Phase 1 output (bundle + routing plan).
- **— LLM DECISION (Planner) —** block with route, justification, confidence.
- No side effects executed.

### 6.2 CodeGen Draft & Scaffold
- Logs show: `codegen_spec_draft` and `codegen_scaffold_rendered` with manifest path.
- Files appear under `agents_generated_specs/drafts/*.md` and `agents/dynamic/<AgentName>/*`.
- **No dynamic load** unless an explicit `--approve` toggle or Gatekeeper approval is simulated.

---

## 7) Pass/Fail Summary for Phase 2

**PASS when:**
- Agents can call a local LLM via `core/llm_client.py`.
- Planner produces an LLM-backed routing decision (printed) and falls back safely on malformed responses.
- Gatekeeper can obtain an advisory rationale from LLM (printed) but still decides deterministically.
- CodeGeneratorAgent can draft specs and render **scaffolds** (files + manifest), but **no auto-exec**.
- Telemetry captures prompts/responses with redaction.
- The demo run (`PHASE2_DEV=1`) shows Phase 1 bundles **and** the LLM decision + codegen draft/scaffold outputs.
- System remains quiet after the demo and exits cleanly on SIGINT.

**FAIL if:**
- Any side effects happen without Gatekeeper approval.
- Model calls are required for boot (no deterministic fallback).
- No printed LLM decision block appears in Phase 2 dev run.
- No codegen scaffold/manifest is produced in dev run.