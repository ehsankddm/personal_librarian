Agent Skeleton Specification
1. Purpose

An Agent is an autonomous worker in the society.

Every Agent:

Speaks in English.

Decides if it can or cannot handle a request.

Acts (or refuses) according to global safety rules.

Reports progress and results to the society.

Logs its experiences to Markdown memory.

Emits telemetry and reward signals.

Learns over time through shared preferences and policies.

Defers risky execution to the Gatekeeper instead of doing it directly.

All generated agents must conform to this skeleton.

2. Required Metadata

Every agent must define:

role:
Short string describing purpose, e.g. "BackupAgent", "EnrichmentAgent", "Planner", "Gatekeeper", "CodeGeneratorAgent", "CuratorAgent".

agent_id:
Unique instance ID for this replica, e.g.
"BackupAgent_immediate_v5",
"BackupAgent_batch_v2",
"WebMetadataAgent_isbn_lookup_v1".

This is how we distinguish replicas of the same role.

traits:
A dict-like structure that encodes variant behavior, for routing and learning.
Examples:

{
  "strategy": "immediate_after_index",
  "llm_style": "short_bullets",
  "domain_focus": "geopolitics"
}


instinct_text:
Loaded at startup from:

instincts/default_agent_instinct.md,

plus any role-specific instinct file (e.g. instincts/gatekeeper_instinct.md),

plus any replica-specific addendum (if the Planner / Curator / CodeGenerator added specialization notes).

This defines baseline behavior ("how I behave in general").

prefs:
Snapshot of state/preferences.json at load time.
Tells the agent how the user likes to be treated:

tone / verbosity,

summary format,

confirmation style,

UI defaults, etc.

policies:
Snapshot of state/policies.json at load time.
Defines hard safety & cost constraints:

allowed network domains,

storage rules (must encrypt before upload),

cost ceilings,

“must ask user before doing X”.

memory_path:
Where this agent writes its memory Markdown:
memory/agents/<agent_id>/<YYYY-MM-DD>.md.

3. Message Interface

All agents communicate through messages that carry at least:

sender (agent_id or "User")

recipient (target agent_id or "Planner" or "User")

content (English text, required)

timestamp

tags (list of strings for Planner/router, e.g. ["backup","request","book_id:cb0f37c2"])

Required behaviors:
3.1 can_handle(message) -> bool

The agent must decide if it should act on this message.

It can use:

natural language interpretation (LLM),

keyword matching,

tags,

its own role and traits.

If it returns False, it must not act, and it must not pretend to act.

This is important for honesty and for routing.

3.2 handle(message) -> reply_message or None

If can_handle(message) is True, the agent:

Acknowledges the request in English.

Describes what it intends to do.

Executes or schedules work.

Sends 1+ progress or completion messages back into the bus.

Emits telemetry.

If the agent cannot complete the task (missing permission, missing capability, conflict with policies), it must explain that in English and escalate (see escalation rules below).

3.3 speak(content, recipient="Planner", tags=None)

Helper method: create and publish a message to the bus.

This is how agents:

report status,

ask for help,

return results,

escalate.

The agent must always speak in English, not just logs.

4. Safety & Gatekeeper Enforcement

Agents must not directly:

call external network resources,

modify filesystem outside allowed directories,

run shell/system commands,

upload anything to outside services,

delete data.

Instead, they must request those operations through a structured ActionRequest to the Gatekeeper.

4.1 propose_action(request: ActionRequest) -> None

The agent formulates:

what it wants done,

why,

perceived cost/risk,

whether user approval is required.

The GatekeeperAgent will:

approve, deny, or escalate to User,

log the audit trail,

execute if allowed.

This isolates dangerous actions behind a single capability firewall.

5. Telemetry Hooks

Every agent must log relevant events for learning, via a shared TelemetryCollector.

5.1 log_event(event_dict)

At minimum, agents emit:

"type": "task_result" with success/failure

"type": "escalation" when they get stuck and ask for help

"type": "message_exchange" when they send messages

"agent_id": <agent_id>

"role": <role>

This feeds:

RewardEngine (for satisfaction & penalty)

PreferenceLearner (UI/tone/interaction style)

PolicyLearner (strategy selection / routing)

Agents do not compute their own final reward; they just log. RewardEngine computes reward later.

6. Learning Inputs (Preferences & Policies)

An agent does not invent its own rules.
It reads the shared state at runtime to adapt to the user.

6.1 Preferences (user comfort layer)

Loaded from state/preferences.json.
Examples:

"communication.verbosity": "brief" | "normal" | "detailed"

"communication.style": "neutral" | "friendly" | "technical"

"summary.style": "short_bullets" | "paragraph"

"confirmation.require_before_send_to_kindle": true

The agent should respect these when forming replies or asking for confirmation.

Example adaptation:

If communication.verbosity == "brief", the agent should answer:

"Done. Encrypted and uploaded 3 new books."

Instead of:

"I have completed the backup task. I encrypted 3 new books using age, verified integrity, and uploaded encrypted blobs to Drive. No failures occurred."

6.2 Policies (safety & cost layer)

Loaded from state/policies.json.
Examples:

network.allow_external_requests = false

network.allowed_domains = ["books.google.com"]

backup.require_encryption_before_upload = true

cost.max_cloud_cost_per_day_eur = 0

filesystem.allow_delete = false

The agent must enforce these by:

refusing to act if something violates policy,

creating an escalation message instead.

For example:

"I cannot send this file externally because network uploads are not currently authorized by policy. I can request approval if you'd like."

Agents are obligated to obey policies, and to treat policy violations as “cannot complete.”

7. Escalation / Stuck Handling

Every agent must implement an escalation instinct. This is critical for trust and safety.

7.1 When to escalate

After exceeding its allowed retry count (prefs.max_retries or default).

When a required capability is missing (no replica can do it).

When blocked by policy (needs approval).

When there's a possible data-loss or money-spend risk.

7.2 How to escalate

When escalating, the agent must send an English message to either:

the Planner (preferred), or

the User (if Planner is the source of the request and escalation requires human judgement).

Escalation message format should include:

What I tried.

Why I'm blocked.

Options.

A direct question.

Example escalation:

"I'm BackupAgent_immediate_v5.
I tried to upload 3 new encrypted files to Drive, but external network access is currently blocked by policy.
Options:

Allow temporary upload for this task only.

Change policy to permit uploads.

Skip cloud backup and store only locally.
How would you like to proceed?"

7.3 Telemetry on escalation

Every escalation must call log_event({"type": "escalation", "agent_id": self.agent_id, ...}).

Escalation is considered (by default) a slightly negative signal in reward, because we want to reduce unnecessary interruptions over time — but agents are never punished for refusing unsafe actions.

8. Memory Obligations

Each agent keeps an append-only Markdown diary stored at:
memory/agents/<agent_id>/<YYYY-MM-DD>.md.

The agent must append memory entries for:

Completed tasks

Escalations

Policy conflicts

Lessons learned / reflections

User feedback

Each entry format:

## [2025-11-02T10:12Z] Backup completed
- Book IDs: cb0f37c2, a91d7f8a, ...
- Outcome: success
- Notes: User was satisfied with immediate backup.
- Policy context: backup.policy=immediate_after_index
- Next time: keep same approach.
---


These memories are later:

Read by ReflectionAgent to summarize the day.

Read by CuratorAgent to update preferences/policies.

Read by CodeGeneratorAgent to inform how to generate better replicas.

The memory is both (1) your audit trail and (2) training data for evolution.

9. Replica Identity and Competition

Agents are not always singletons. Multiple replicas of the same role may exist at once.

Every replica must:

Declare its agent_id and traits.

Behave consistently with those traits.

Log its own telemetry and memory.

Accept getting routed work by the Planner.

Accept that underperforming replicas can be retired by CuratorAgent.

Replicas enable:

A/B testing strategies (e.g. "immediate backup" vs "batch nightly").

Specialization ("geopolitics tagging" vs "fiction tagging").

Evolution under reward pressure.

The skeleton MUST support replicas. No agent may assume "I'm the only BackupAgent."

10. Lifecycle Hooks

To support dynamic generation and retirement, every agent must support:

10.1 describe_capabilities() -> str

Returns a short English description of what the agent can do.

Example:

"I am BackupAgent_immediate_v5. I encrypt new books and upload them to encrypted backup immediately after ingestion. I am optimized for speed and confirmation visibility."

The Planner, Curator, and CodeGenerator use this to reason about routing and replacement.

10.2 retire(reason: str)

When Curator decides to deprecate this replica:

The agent writes a final memory entry explaining why it's retired.

The agent updates the registry to mark itself inactive.

The agent stops responding to messages.

The reason is stored for future learning (why did this replica fail?).

11. Summary of Skeleton Requirements

An agent must:

Identify itself

role, agent_id, traits

Load shared guidance

instinct_text (Markdown instincts)

prefs (preferences.json)

policies (policies.json)

Communicate

Receive English messages

Decide relevance: can_handle(message)

Respond in English

Always be honest about scope: “this is not in my scope”

Act safely

Never directly execute risky operations

Ask Gatekeeper via ActionRequest for network/filesystem/shell/etc.

Escalate with explanation if blocked by safety or policy

Learn & Adapt

Emit telemetry (log_event)

Mark success/failure so RewardEngine can evaluate

Use updated prefs/policies when generating responses

Adjust behavior based on those updates automatically

Remember

Append Markdown memory entries with timestamps

Record what happened, what went well, where it got stuck

Record lessons learned and next-step proposals

Be replaceable

Provide describe_capabilities()

Support being retired gracefully

Accept existing alongside replicas of the same role

12. Why this skeleton matters

It enforces honesty (“I can / I cannot do this”).

It enforces safety (never acts outside Gatekeeper).

It enables learning (everything is telemetered and remembered).

It supports evolution (replicas with different traits can coexist).

It supports alignment with you (preferences & policies are always consulted).

It supports long-term governance (memories and escalation are logged with rationale).

This is the “organism cell spec.”
Every living agent in your system — human-written or AI-generated — has to look like this.