💡 Roadmap (Implementation Phases)
Phase	Focus	Outcome
0. Kernel	Implement Bus, Planner, Gatekeeper, Interface, Memory, Learning skeletons.	Bootable society core.
1. Self-Expression	English message flow + logging.	Conversational coordination.
2. Code Generation	CodeGeneratorAgent + dynamic loader.	Can spawn new agents safely.
3. Learning Loop	Telemetry, rewards, preferences, policies.	Adaptive behavior.
4. Domain Agents	Ingestion, Backup, Enrichment, Metadata.	Full librarian functionality.
5. Reflection & Evolution	Curator and ReflectionAgent evolve instincts.	Continuous self-improvement.
🧩 Example Boot Process

Planner reads society_values.md and policies.

InterfaceAgent starts and listens for user input.

You say: “Import my new books from Drive.”

Planner can’t find an ingestion agent → asks CodeGenerator to create one.

Gatekeeper approves safe access to Google Drive.

IngestionAgent completes the task, logs results.

Curator rewards success (+1), logs improvement.

ReflectionAgent summarizes the day in memory/society/.

🚀 Outcome

Fully transparent, agentic, and evolving system.

Controlled, interpretable self-improvement.

Safe, local-first operation respecting privacy and cost.

Modular foundation for any future AI-assisted workflows.

🧩 Summary: The System in One Sentence

A self-evolving, language-driven society of software librarians that safely manage, learn from, and improve how they handle your personal library.

## ➕ Phase 2 Addenda (Context Added, Not Modifying Original)

- LLM Gateway Integration
  - Added a local OpenAI-compatible gateway client (`core/llm_client.py`).
  - Env-based config via `.env`: `LLM_BASE`, `LLM_API_KEY`, `LLM_MODEL_ALIAS`, `LLM_TIMEOUT`.
  - Planner prints an LLM-backed routing decision (chosen_route, justification, confidence, needs_user_confirmation) in dry-run mode.

- Gatekeeper Advisory (Non-Binding)
  - GatekeeperAgent can request an LLM-generated risk rationale and suggested decision; final decisions remain deterministic and policy-driven.

- Safe Code Generation (Scaffolds Only)
  - CodeGeneratorAgent drafts specs to `agents_generated_specs/drafts/` and writes a minimal scaffold + `MANIFEST.json` under `agents/dynamic/<AgentName>/`.
  - No auto-exec: two explicit user-driven steps were added (approval phrases typed in CLI):
    - "approve load [agents/dynamic/<AgentName>/MANIFEST.json]" → Gatekeeper → Loader → Registry (quarantined)
    - "activate agent <AgentName>" → Gatekeeper → instantiate + subscribe → Registry (active)

- Telemetry & Persistence
  - All bus messages (published + dispatched) persist to SQLite `state/telemetry.db` in a new `messages` table.
  - Existing telemetry table records LLM prompts/responses (with redaction) and codegen events.
  - Example queries are now documented in README to inspect the last N minutes of activity.

- Developer UX
  - Interactive CLI is enabled by default; Phase 2 demo is toggled with `PHASE2_DEV=1`.
  - InterfaceAgent remains the single interaction surface; Planner communicates to the user by creating tasks/messages for InterfaceAgent.

- Behavior Notes (Expected During Phase 2)
  - Until an approved scaffold is loaded and activated, the underlying capability remains missing; repeated requests can naturally re-trigger codegen unless gated by approval.
  - The explicit approve-load and activate-agent flows resolve that blocker without weakening safety.

- Next Steps (Beyond Phase 2, Informational)
  - Path capture and other configuration prompts should be surfaced via InterfaceAgent as Planner-determined tasks (schema-driven), then persisted to `state/preferences.json`.
  - Activate loaded agents as routable candidates only after passing basic self-tests and policy checks (quarantine → active lifecycle).

### See Also
- Phase 2 CLI phrases and approval flow: see README “Phase 2 — LLM + Safe Codegen”.
- Telemetry DB and queries: see README “Telemetry & Message Persistence”.
