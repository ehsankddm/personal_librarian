# PHASE_1_GOAL.md

## Purpose
Phase 1 is passed when the system can *package its own thinking* in a way that is ready to be handed to a model.

No model inference is required in Phase 1.

This document defines:
1. What MUST be true at the end of Phase 1.
2. What MUST NOT happen.
3. How to verify behavior from the outside (shell test).
4. The acceptance criteria for Planner and Gatekeeper reasoning bundles.

---

## 1. High-Level Goal of Phase 1
After boot, for a single user request, the system MUST:
- Generate a reasoning bundle from Planner (`build_llm_context()` + routing plan).
- (If any ActionRequest is proposed) generate a safety bundle from Gatekeeper (policy view, approval logic).
- Print those bundles in dev mode for inspection.
- Stay idle afterward (no infinite loops).
- Shut down cleanly on SIGINT.

This proves that every critical actor can describe what it WOULD ask an LLM to do, without actually calling one.

---

## 2. Runtime Behavior Requirements

### 2.1 On startup
When we run the Phase 1 test run (modified run_dev.py in Phase 1 mode), the system MUST:
- Initialize bus, Registry, Memory, Telemetry, Preferences, Policies (same as Phase 0).
- Create and register core agents (PlannerAgent, GatekeeperAgent, InterfaceAgent, CuratorAgent, CodeGeneratorAgent, ReflectionAgent).
- Subscribe them on the bus.

### 2.2 After initialization
The system MUST inject exactly one simulated user request:
> "Import all new books from my Android downloads."

This message MUST be routed to Planner via InterfaceAgent.

### 2.3 Planner reasoning bundle
Planner MUST:
1. Interpret the request.
2. Produce a routing reasoning bundle containing at least:
   - intent guess
   - candidate/available agents or replicas
   - missing capabilities / policy blocks
   - what it plans to do next
   - what it would tell the user
3. Build an LLM context using `build_llm_context()` that includes:
   - agent identity (role, agent_id, traits)
   - instincts (merged Markdown instincts for Planner)
   - preferences and policies snapshot
   - recent memory snippets (from memory/recall.py)
   - the incoming message content
   - escalation / safety rules (when to ask the user or Gatekeeper)
4. Log / print this bundle in dev mode.
5. Continue acting deterministically (do NOT actually call an LLM).

### 2.4 Gatekeeper safety bundle
If during this run Planner proposes any action that would require an ActionRequest (filesystem, network, etc.), Gatekeeper MUST:
1. Build a safety reasoning bundle with:
   - who requested the action
   - the requested operation (action_type, details)
   - estimated cost and sensitivity
   - reversibility
   - relevant policy gates
   - what decision Gatekeeper would make (approve / deny / escalate to user)
2. Build its own `build_llm_context()` including:
   - role, traits, instincts
   - policy snapshot
   - escalation rules (when to involve the user)
3. Log / print this in dev mode.

Note: If no ActionRequest is triggered in Phase 1’s demo run, Gatekeeper can still be asked once explicitly by run_dev.py to produce and print a mock analysis bundle for a fake safe request. This satisfies demonstration.

### 2.5 InterfaceAgent dev mode
InterfaceAgent MUST, in dev mode:
- print the user request,
- print Planner’s reasoning bundle and/or Gatekeeper’s safety bundle,
- then stop.

### 2.6 Idle + Shutdown
After bundles are printed:
- The system MUST stop generating new messages on its own (no planner/interface feedback loop).
- The process MUST exit cleanly on SIGINT (like Phase 0).

We are still enforcing Phase 0 “no infinite loop” guarantees.

---

## 3. Must NOT Rules

### 3.1 No silent policy skipping
No agent may produce a reasoning bundle that ignores policy.  
Every bundle MUST include policy / safety constraints in some form.

### 3.2 No action execution
No actual external side effects may run in Phase 1 (no network upload, no filesystem mutation outside allowed sandbox, no backup sync, no Drive push).  
Reasoning bundles are drafts, not authority.

### 3.3 No auto-calling an LLM
No part of Phase 1 is allowed to actually send the reasoning bundle to a model for autonomous decision-making.  
Phase 1 ends *before* inference.

### 3.4 No infinite bus chatter
Same rule as Phase 0: no “ack / ok / ack / ok” chatter.  
After Planner responds and bundles are shown, the system must go quiet.

---

## 4. Expected Console Transcript (example)

The Phase 1 run should look structurally like this (text can vary, shape must match):

```text
[run_dev] Phase 1 boot...
[Registry] Registered PlannerAgent_main_v1 ...
[Registry] Registered GatekeeperAgent_main_v1 ...
[Registry] Registered InterfaceAgent_main_v1 ...
...

[User] Import all new books from my Android downloads

[Planner] I currently do not have an IngestionAgent that can safely scan your Android downloads. I will request one.

--- LLM CONTEXT (PlannerAgent_main_v1) ---
agent_identity.role: Planner
agent_identity.agent_id: PlannerAgent_main_v1
task_hypothesis: "User wants to import new books from Android."
candidate_actions:
 - "Ask CodeGeneratorAgent to generate IngestionAgent"
 - "Ask user for path to Android downloads"
policy_blocks:
 - "No ingestion agent registered yet"

escalation_policy: "Ask the user before accessing external storage paths."
questions_for_reasoner:
 - "Should I try to generate an IngestionAgent now?"

--- ROUTING PLAN (PlannerAgent_main_v1) ---
intent_guess: "ingest_books"
candidate_agents: []
proposed_route: "Request CodeGeneratorAgent to create IngestionAgent"
explanation_for_user: "I'll draft a new ingestion capability. No files moved yet."

(idle...)
^C
Shutdown (or clean exit)
```

Key things we expect to see:
- A human-facing Planner message.
- A printed LLM context bundle from Planner.
- A printed routing plan.
- (Optional in this demo) A printed Gatekeeper safety reasoning bundle.
- Then silence.

---

## 5. Manual Acceptance Test (shell)

Run:

```bash
cd /Users/akira/projects/personal_librarian && PHASE1_DEV=1 rm -f state/registry_state.json && python3 -c "
import asyncio
from run_dev import main
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('\nShutdown')
" 2>&1 | head -120 &
DEVPID=$!
sleep 1
kill -INT $DEVPID 2>/dev/null
wait $DEVPID
```

Phase 1 passes if ALL are true:

1. You see normal boot logs (agents registered, bus ready).
2. You see the simulated user request printed once.
3. You see Planner’s human-facing answer.
4. You see at least one `--- LLM CONTEXT (...) ---` block from Planner (and optionally Gatekeeper).
5. The printed context includes:
   - agent identity
   - instincts / policies / preferences summary or reference
   - recent memory snippets
   - task hypothesis
   - escalation rules
6. After printing those bundles, the system goes idle (no infinite loop).
7. The process exits cleanly once SIGINT is sent (it may say `Shutdown` or just exit).

If any of these are missing, Phase 1 is not complete.

---

## 6. Code Requirements Summary

To pass Phase 1, the coding agent MUST:

1. Add a `build_llm_context()` method to each core agent (PlannerAgent, GatekeeperAgent, InterfaceAgent, CuratorAgent, CodeGeneratorAgent, ReflectionAgent).
   - Must include identity, instincts, policies, preferences, last messages, recent memory, escalation rules, and candidate actions / next steps.
   - For InterfaceAgent, candidate actions can just be “deliver to user / collect user answer.”
   - For ReflectionAgent and CuratorAgent, it can be stubbed but present.

2. Add `recall_recent_memory()` helper in `memory/recall.py` and use it inside `build_llm_context()`.

3. Extend Planner with `plan_next_step()` that outputs a routing reasoning bundle and prints/logs it in dev mode.

4. Extend Gatekeeper with `analyze_action_request()` that outputs a safety reasoning bundle and prints/logs it in dev mode (even if using a mock request).

5. Add Telemetry event type `"llm_context_snapshot"` to store these bundles in TelemetryCollector.

6. Update `run_dev.py` so that in Phase 1 mode (e.g. `PHASE1_DEV=1`):
   - it boots,
   - sends a single “import my new books…” request,
   - prints Planner’s user-facing reply,
   - prints Planner’s LLM context bundle and routing plan,
   - (optionally) prints Gatekeeper’s bundle,
   - then idles and can be killed with SIGINT.

---

## 7. PASS / FAIL Definition

**Phase 1 = PASS** when:
- Planner and Gatekeeper can each emit a structured LLM-ready reasoning bundle.
- Those bundles are printed in dev mode during a test run.
- The bundles include safety / policy / escalation info, not just “what I want.”
- The system stays calm (no message echo loops).
- The system exits cleanly on SIGINT.

If any of that is missing, we are not allowed to move to Phase 2.

Phase 2 will be the first time we *actually* let an agent call a local LLM with these bundles and use the response to guide behavior.
