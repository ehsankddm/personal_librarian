now that you’ve got agents and actions specified, the next critical piece is the Planner, since it’s the central nervous system of your evolving society.

Let’s define it cleanly and systematically, so every other part — agents, Gatekeeper, learning — plugs into it seamlessly.

🧭 Planner Specification
1. Purpose

The Planner is the central coordinator and router.
It ensures that every user request, internal goal, or agent message finds the right executor — safely, efficiently, and in line with learned preferences and policies.

It is not omnipotent; it’s more like a strategic project manager:

decomposes high-level tasks into subtasks,

routes subtasks to suitable agents or replicas,

monitors progress and aggregates results,

decides when to escalate (to Curator, CodeGenerator, or User),

and constantly learns which routing patterns produce best results.

2. Planner’s Core Roles
Function	Description
Interpretation	Understand user or agent requests written in English.
Decomposition	Break complex goals into smaller steps or capabilities.
Routing	Pick which agent/replica should handle each subtask.
Monitoring	Track progress and update memory.
Escalation	Ask Curator or User for help when no available agent can handle a task.
Recruitment	Request CodeGeneratorAgent to create new agents if a capability is missing.
Reflection	Record which strategies worked best (for learning).
3. Key Components
Component	Description
Message Interpreter	Converts natural language into structured task intents.
Registry Connector	Reads from core/registry.py to see available agent replicas and their stats.
RouterLearner Connector	Consults learning layer to choose best replica for a given intent/context.
Policy Filter	Filters out replicas disallowed by policies (e.g., network restrictions).
Telemetry Logger	Logs routing decisions, success, failures, escalations.
Memory Writer	Writes daily planning summaries into memory/society/<date>.md.
4. Input/Output Interface

Planner communicates through English messages, like every agent, but its messages are more “directive.”

Example input:

From User via InterfaceAgent:

“Import all new books from my Android downloads.”

Example internal steps:

Parse goal: “import books” → task type ingestion.

Check registry for agents with role IngestionAgent.

If none found → ask CodeGeneratorAgent to create one.

When created → send the ingestion task to the new agent.

Log the whole flow to society memory.

Example output:

To User:

“I’ve created a new IngestionAgent to handle your request. It will now scan your Android downloads folder and import books.”

5. Planner Workflow
5.1 High-Level Flow
receive_message()
  ↓
interpret_intent()  ← LLM-based or rule-based
  ↓
find_candidates(intent)
  ↓
filter_by_policy_and_scope()
  ↓
rank_candidates(intent, context)
  ↓
route_to_best(candidate)
  ↓
monitor_progress()
  ↓
reward_feedback()

5.2 Step-by-step breakdown
(1) interpret_intent(message)

Parses message content into a task intent object:

{
  "task_type": "ingest_books",
  "goal": "import all new books",
  "entities": ["Android downloads folder"],
  "urgency": "normal",
  "context": "user_request"
}


Adds tags like ["ingestion", "new_books", "user_request"] to help with routing.

(2) find_candidates(intent)

Queries core/registry.py for active replicas that claim relevant capabilities (based on their role, traits, and describe_capabilities()).

(3) filter_by_policy_and_scope()

Uses policies.json and preferences.json to prune candidates:

If policy.network.allow_external_requests = false, skip any replica requiring network access.

If policy.backup.require_encryption_before_upload = true, prefer replicas that comply.

(4) rank_candidates(intent, context)

Consults learning/router_learner.py:

Uses reward history to rank replicas.

Factors in domain (e.g. “fiction tagging” vs. “technical metadata”).

Chooses the one with the highest expected success given the current context.

(5) route_to_best(candidate)

Sends message to the selected replica via MessageBus.

Logs telemetry:

{
  "event": "route",
  "planner_decision": {
    "intent": "ingest_books",
    "chosen_agent": "IngestionAgent_v3",
    "alternatives_considered": 3
  }
}

(6) monitor_progress()

Watches for messages with tags like ["progress", "complete", "escalation"].

If escalation occurs:

Analyze reason.

If “missing capability” → request CodeGeneratorAgent to spawn a new agent.

If “blocked by policy” → ask User for decision.

If “error” → log to memory, notify Curator.

(7) reward_feedback()

Once task completes successfully or fails, logs success/failure.

RewardEngine updates replica and routing policy performance.

6. Handling Missing Capabilities

Planner instinctually knows when something is “not in scope.”

If no registered agent claims capability for a task:

Planner drafts a capability spec in English:

“I need an agent that can fetch and parse metadata from online book databases via ISBN lookup.”

Writes it to /agents_generated_specs/requested_capabilities/<uuid>.md.

Sends message to CodeGeneratorAgent:

“Please create an agent for this spec.”

Waits for the new agent to register in registry.json.

Routes the original task once ready.

7. Escalation Rules

If Planner cannot progress due to:

missing capability,

policy block,

ambiguous user intent,

or repeated agent failures,

it must escalate.

7.1 To CuratorAgent:

“I’ve noticed repeated backup policy denials. Perhaps we should adjust the backup policy cadence or encryption strategy?”

7.2 To User:

“No available agent can fetch external metadata right now because network access is disabled. Would you like to enable it temporarily?”

Planner must never silently fail.

8. Learning Hooks

Planner is a learning participant, not static logic.

8.1 Reward inputs:

Routing success/failure.

User satisfaction (explicit or inferred).

Policy adherence (bonus reward if no violations).

Escalation count (minor penalty).

8.2 Router Learner integration:

Keeps table:

(task_type, context, agent_id) → average_reward


Uses softmax sampling or weighted choice to route future tasks.

Exploration/exploitation balance controls how much Planner experiments with new replicas.

8.3 Reflection:

At the end of each day, Planner writes to memory/society/<date>.md:

## [2025-11-02T23:00Z] Daily Summary
- 14 tasks routed.
- 11 completed successfully.
- 2 new agents spawned (WebMetadataAgent, BackupAgent_incremental).
- 1 policy violation blocked by Gatekeeper.
- User satisfaction: +0.8 avg.
- Action: Recommend deprecating BackupAgent_batch_v2.

9. Policies & Instinct Integration

Planner reads:

instincts/planner_instinct.md: defines its meta-behavior (“coordinate, don’t dominate”).

policies.json: defines what’s allowed globally.

preferences.json: defines how user likes it to communicate (“verbose status updates” vs “minimal notifications”).

Planner also respects the same escalation instinct as all other agents.

10. Safety Constraints

Planner cannot directly execute ActionRequests.
Only delegates tasks and may request CodeGeneratorAgent to produce new agents.

Planner also:

cannot change locked policy keys,

must ask for confirmation before enabling high-cost capabilities,

must record all high-impact routing decisions in society memory.

11. Example Planner Lifecycle

User:
“Can you back up my new books?”

Planner:

Checks registry: finds 3 BackupAgent replicas.

RouterLearner says BackupAgent_immediate_v5 is most successful recently.

Confirms policy allows encryption + upload.

Sends backup request to that replica.

BackupAgent:

Submits ActionRequest to Gatekeeper for upload.

Gets approval → success → logs telemetry.

Planner:

Receives “backup complete” message.

Logs reward for that replica.

Updates society memory.

12. Summary of Guarantees
Guarantee	Mechanism
No lost tasks	Planner tracks every message’s lifecycle.
No unsafe behavior	All external actions flow through Gatekeeper.
Continuous improvement	Routing informed by reward and policy learning.
Self-expansion	Missing capabilities lead to new agent generation.
Transparency	Every decision logged in Markdown memory.
User control	Escalations for ambiguity or risk always ask you first.
13. Key Interfaces (for Implementation)
Method	Responsibility
receive_message(message)	Entry point for new message or user request.
interpret_intent(message)	Extracts goal, entities, task type.
find_candidates(intent)	Queries registry for matching roles/traits.
rank_candidates(intent, context)	Consults RouterLearner to pick best replica.
route(intent, agent_id)	Sends message to chosen replica.
handle_escalation(message)	Responds to blocked or failed tasks.
summarize_day()	Writes daily log to society memory.
🧩 Summary

The Planner:

is the heart of coordination,

speaks English like any agent,

uses learned preferences/policies to make routing decisions,

generates new agents when needed,

enforces safety by staying within policy boundaries,

learns from telemetry and user satisfaction,

and keeps society memory transparent and traceable.
