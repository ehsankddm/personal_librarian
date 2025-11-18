# PHASE 2 — Goals & Acceptance Criteria

Phase 2 is considered **PASSED** when the system can **use a local LLM** to assist routing and code generation **safely**, with strong fallbacks and no unapproved side effects.

---

## 1) Goals

1. **Planner LLM-Assisted Routing (Dry-Run)**
   - Given a Phase 1 context bundle and deterministic candidates, the Planner calls the local LLM and prints a decision block:
     - `chosen_route`, `justification`, `confidence`, `needs_user_confirmation` (JSON-backed).
   - If the LLM output is malformed or missing, Planner falls back to deterministic `plan_next_step()`.

2. **Gatekeeper Advisory (LLM Rationale, Non-Binding)**
   - Gatekeeper can optionally ask the LLM for a risk rationale and suggested outcome.
   - Gatekeeper **still** decides deterministically using current policies.

3. **Code Generation Scaffolds (No Auto-Exec)**
   - CodeGeneratorAgent drafts a Markdown spec and renders a minimal scaffold into `agents/dynamic/<AgentName>/` with a `MANIFEST.json` (hashes + self-test command).
   - Dynamic loading requires explicit approval—no auto-run in Phase 2.

4. **Telemetry & Redaction**
   - Telemetry records prompts/responses (with basic redaction), codegen events, and dynamic loader approvals/denials.

5. **Determinism & Fallbacks**
   - If the local LLM is unavailable, Phase 2 demos still complete by using Phase 1 logic.

---

## 2) Non-Goals / Must-Not (Phase 2)

- No external side effects execute automatically from LLM output.
- No network, filesystem mutation, or dynamic loading without **Gatekeeper approval**.
- No implicit policy changes; learning loops remain **disabled** (that’s Phase 3).
- No long-running background LLM sessions that bypass token/time limits.

---

## 3) Demo Run (Manual Acceptance Test)

Run the Phase 2 demo:

```bash
cd /Users/akira/projects/personal_librarian && rm -f state/registry_state.json state/telemetry.db && PHASE2_DEV=1 python3 -c "
import asyncio
from run_dev import main
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('\\nShutdown')
" 2>&1 | sed -n '1,200p'
```

**We must see (structure, not exact text):**

1. **Phase 1 bundles first** (LLM context + routing plan printed).  
2. **Planner LLM Decision block** like:
   ```
   — LLM DECISION (Planner) —
   chosen_route: Request CodeGeneratorAgent to create AndroidIngestionAgent_v1
   justification: "..."
   confidence: 0.74
   needs_user_confirmation: true
   ```
3. **CodeGen outputs**:
   - `codegen_spec_draft` log + path under `agents_generated_specs/drafts/*.md`
   - `codegen_scaffold_rendered` + `MANIFEST.json` path under `agents/dynamic/<AgentName>/`
4. **Gatekeeper advisory (optional in demo)** printed once for a mock ActionRequest.
5. **No side effects executed**, no dynamic load unless flagged (e.g., `--approve-load` or env var).  
6. **Process idles and exits cleanly** on SIGINT.

**If any of these are missing → Phase 2 is not passed.**

---

## 4) Spot Checks (What Reviewers Should Verify)

- Planner prints both deterministic plan **and** LLM decision; fallback tested by simulating a malformed LLM output.
- CodeGeneratorAgent writes files, manifest has correct SHA-256 for each file.
- Loader refuses to load the new agent unless Gatekeeper approval path is executed.
- Telemetry shows: `llm_prompt`, `llm_response`, `codegen_spec_draft`, `codegen_scaffold_rendered` (with redaction enabled).
- Logs include token/time budgets and no overruns.

---

## 5) Minimal Changes Needed by Each Component

- **core/llm_client.py** — new pluggable client; mock backend included.
- **agents/planner_agent.py** — add `reason_with_llm()` and dev prints.
- **agents/gatekeeper_agent.py** — add `advise_on()` and dev prints.
- **agents/code_generator_agent.py** — draft spec, render scaffold, write manifest.
- **core/loader.py** — sandboxed dynamic loader; returns class reference or error.
- **core/registry.py** — `register_dynamic_agent()` with provenance metadata.
- **learning/telemetry_collector.py** — new events + redaction.
- **run_dev.py** — add `PHASE2_DEV` path demonstrating LLM decision and codegen flow.

---

## 6) PASS / FAIL Definition

**PASS** when all of the following are true:
- LLM decision block prints (Planner) and deterministic fallback works.
- Gatekeeper advisory prints at least once (or can be triggered with a flag).
- Codegen spec + scaffold + manifest are created on disk.
- No dynamic load without explicit approval.
- Telemetry logs new events with redaction.
- Demo run idles and exits cleanly on SIGINT.

**FAIL** if any safety gate is bypassed, if no LLM decision block is printed, or if codegen artifacts are missing.