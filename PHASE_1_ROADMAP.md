# PHASE_1_ROADMAP.md

## Phase 1 Name
**Phase 1 — Self-Expression & LLM Context Packaging**

Phase 0 gave us a living society kernel: agents can boot, talk over the bus in English, respect safety, escalate through Planner, and stop without spinning forever.

Phase 1 is about preparing this society to *think*. We are not calling an LLM to make decisions yet. We are teaching every core agent how to assemble and expose its own context bundle so that, in Phase 2, those bundles can be sent directly to a reasoning model to drive actual decisions, plans, and tool calls.

In other words: Phase 1 makes the system explainable, inspectable, and LLM-ready.

---

## High-Level Objectives
1. Every agent can summarize who it is, what it’s seeing, what it thinks it should do next, and what it’s allowed to do — as a structured reasoning bundle.
2. Planner and Gatekeeper can request those bundles from themselves and from other agents.
3. The system can emit those bundles to logs / stdout for inspection when handling a request.
4. No agent actually *delegates* decisions to an LLM yet. Phase 1 is about packaging, not inference.
5. The bus, Registry, and Memory are updated so that future LLM calls in Phase 2 have access to preferences, policies, instincts, and recent memory.

---

## Why this matters
- We need a stable prompt contract before we involve any real model.
- We need deterministic, reviewable “what would I ask the model?” output for safety and debugging.
- We want to guarantee that future LLM calls will always include safety constraints (policies), the agent’s identity, and escalation rules.

This prevents hallucinated authority, prevents silent policy violations, and gives us an auditable trace of intent before we ever let a model act.

---

## Scope of Phase 1

### 1. Add `build_llm_context()` to all core agents
Each agent class (PlannerAgent, GatekeeperAgent, InterfaceAgent, CuratorAgent, CodeGeneratorAgent, ReflectionAgent) must implement:

```python
def build_llm_context(self, incoming_message) -> dict:
    return {
        "agent_identity": {
            "role": self.role,
            "agent_id": self.agent_id,
            "traits": self.traits,
        },
        "instincts": self.instinct_text,            # merged society_values + role instinct + replica notes
        "policies": self.policies,                  # snapshot of state/policies.json relevant to this agent
        "preferences": self.preferences,            # snapshot of state/preferences.json relevant to UX/tone/confirmation
        "recent_memory": <list of recent memory snippets>,
        "incoming_message": {
            "sender": incoming_message.sender,
            "content": incoming_message.content,
            "tags": incoming_message.tags,
        },
        "task_hypothesis": <what this agent THINKS the user/Planner wants>,
        "candidate_actions": <what this agent THINKS it could do next, in English>,
        "escalation_policy": <when this agent MUST escalate instead of acting>,
        "questions_for_reasoner": <what this agent wants answered>,
    }
```

Notes:
- Phase 1 does **not** need perfect summaries of memory or policies. Reasonable slices are fine.
- Phase 1 must *always include* escalation limits and Gatekeeper constraints so we never ask an LLM to violate policy in Phase 2.
- This is the “reasoning bundle.” This bundle will later become the prompt for the LLM in Phase 2.

### 2. Add `recall_recent_memory(agent_id, max_items=N)`
Implement a helper in `memory/recall.py` that can return recent Markdown memory snippets for an agent (and optionally for society).

Agents will call this inside `build_llm_context()` to populate the `recent_memory` field with relevant bullets, not the entire diary file.

Requirements:
- Must return human-readable snippets with timestamps.
- Must not return gigantic blobs (cap length).
- Must not remove anything from disk.

### 3. Extend Planner to generate a “routing reasoning bundle”
PlannerAgent gains a `plan_next_step(incoming_message)` method that:
- calls `self.build_llm_context(incoming_message)`,
- adds planner-specific routing state (candidate replicas from Registry, policy filters, etc.),
- returns a structured plan object like:

```python
{
  "intent_guess": "...",
  "candidate_agents": ["BackupAgent_immediate_v5", "BackupAgent_batch_v2"],
  "policy_blocks": ["network uploads disabled"],
  "proposed_route": "Ask CodeGeneratorAgent to create IngestionAgent",
  "explanation_for_user": "I don't yet have an agent that can scan your Android downloads safely."
}
```

For Phase 1, Planner still acts deterministically the same way as Phase 0.  
But now it *also* logs this plan object to stdout / memory/society for auditing.  
In Phase 2, this object becomes “LLM, choose the best route.”

### 4. Extend Gatekeeper to generate a “safety reasoning bundle”
GatekeeperAgent gains `analyze_action_request(request)` that:
- builds a context (who requested, what the request is, relevant policies, reversibility, cost, sensitivity),
- creates a human-readable summary: approve / deny / ask user,
- and logs that summary.

In Phase 1 Gatekeeper still uses deterministic logic to make the decision.  
But it also logs: “If I asked an LLM, here is what I would send it, and here’s what I decided.”  
In Phase 2 that bundle can be used to draft escalation messages to the user.

### 5. Update Telemetry
TelemetryCollector should gain a new event type, e.g. `"llm_context_snapshot"`, which stores:
- agent_id
- incoming message summary
- build_llm_context() output (or redacted form)

This gives us a record of “what we would have asked the model” for later review.

### 6. InterfaceAgent Developer Mode
InterfaceAgent should gain a dev-mode toggle (env var, CLI arg, or run_dev flag).  
In dev mode it should print LLM context bundles for human inspection each time a user request is routed, e.g.:

```text
--- LLM CONTEXT (PlannerAgent_main_v1) ---
agent_identity.role: Planner
task_hypothesis: "User wants to import new books from Android."
candidate_actions:
 - "Ask CodeGeneratorAgent to generate IngestionAgent"
 - "Ask user for path to Android downloads"
policy_blocks:
 - "No ingestion agent registered yet"

escalation_policy: "Ask the user before accessing external storage paths."
questions_for_reasoner:
 - "Should I try to generate an IngestionAgent now?"
```

We do not call any model yet, we just surface what WOULD have been asked.

### 7. Update run_dev.py for Phase 1 mode
`run_dev.py` should:
- boot the society like Phase 0,
- send the same sample request (“Import all new books from my Android downloads”),
- capture the Planner’s reasoning bundle and Gatekeeper’s bundle (if any),
- print them once for inspection,
- idle,
- and exit cleanly on SIGINT.

This becomes the acceptance test for Phase 1.

---

## Out of Scope for Phase 1
- Actually calling an LLM.
- Letting an LLM generate code.
- Letting an LLM change policies or preferences.
- Letting any agent actually perform filesystem, network, backup, or ingestion actions beyond what Phase 0 already protects.

All of that moves to Phase 2 (LLM in the loop) and Phase 3 (learning loop).

---

## Deliverables for Phase 1
1. `build_llm_context()` implemented for all core agents (PlannerAgent, GatekeeperAgent, InterfaceAgent, CuratorAgent, CodeGeneratorAgent, ReflectionAgent).
2. `recall_recent_memory()` helper in memory layer to support context bundling.
3. Planner emits a structured “routing reasoning bundle” for each user request.
4. Gatekeeper emits a structured “safety reasoning bundle” for each ActionRequest it evaluates.
5. Telemetry logs snapshot of each reasoning bundle.
6. run_dev.py (Phase 1 mode) demonstrates one full request, shows bundles, then idles.

---

## Success Criteria
By the end of Phase 1:
- We can point to any agent and ask: “What would you have told the LLM about this situation?”
- We can read that bundle as Markdown / JSON in logs.
- We can reproduce that bundle deterministically.
- We can verify the bundle always includes safety, policy, escalation, and limits.


