Let's define the Registry & Replica Management spec.
This is the book of life for your system: who exists, what they can do, how good they are, and whether they’re still trusted.

We'll treat this as a standalone spec you can implement in core/registry.py.

🗂 Registry & Replica Management Specification
1. Purpose

The Registry is the source of truth for:

Which agents exist right now.

Which replicas of each role are active.

What each replica claims it can do.

How well each replica is performing.

Which replicas are allowed to receive work.

Which replicas have been retired (and why).

The Planner, CuratorAgent, CodeGeneratorAgent, and RouterLearner all depend on the Registry.

Think of the Registry as:
"Who’s on the team, what are they good at, and should we keep routing work to them?"

2. High-Level Responsibilities

The Registry must:

Register new agent replicas when they come online.

Store metadata about each replica’s capabilities, traits, and safety posture.

Track performance and reward stats over time.

Expose query methods so Planner can choose candidates.

Mark replicas inactive (retired) when Curator decides they’re no longer useful or safe.

Persist state (so the society survives restarts).

Provide information in human-readable form for memory and audits.

3. Core Concepts
3.1 Role

A logical function type, e.g.:

"BackupAgent"

"IngestionAgent"

"EnrichmentAgent"

"WebMetadataAgent"

"Planner"

"CuratorAgent"

Multiple replicas can share the same role.

3.2 Replica

A concrete instance of that role, with its own ID and behavioral traits.

Example:

BackupAgent_immediate_v5

traits: {"strategy": "immediate_after_index"}

BackupAgent_batch_v2

traits: {"strategy": "batch_nightly"}

Replicas are how you:

explore different strategies,

specialize for certain book domains,

A/B test policies,

evolve the society.

3.3 Status

Each replica has a lifecycle status:

"active": Planner can route work to it.

"quarantined": Temporarily disabled (policy violation, risky behavior, high escalation rate).

"retired": No longer used. Remains in the registry for memory and reference.

Planner should only consider "active" replicas.
CuratorAgent can flip status.

4. Data Model

The Registry should maintain an in-memory view and persist it to disk (e.g. state/registry_state.json).

For each replica:

{
  "agent_id": "BackupAgent_immediate_v5",
  "role": "BackupAgent",

  "traits": {
    "strategy": "immediate_after_index",
    "llm_style": "short_bullets",
    "domain_focus": "geopolitics"
  },

  "instinct_paths": [
    "instincts/default_agent_instinct.md",
    "instincts/gatekeeper_instinct.md"
  ],

  "status": "active",       // "active" | "quarantined" | "retired"
  "alive": true,            // runtime liveness flag

  "capabilities_summary": "I encrypt new books and immediately back them up to Drive after ingestion. I specialize in geopolitics material.",

  "created_at": "2025-11-02T10:04:22Z",
  "last_active_at": "2025-11-02T11:31:10Z",
  "retired_at": null,
  "retire_reason": null,

  "safety_profile": {
    "needs_network": true,
    "touches_user_data": true,
    "irreversible_ops_possible": false
  },

  "performance": {
    "success_count": 14,
    "failure_count": 1,
    "escalation_count": 2,

    "avg_reward": 0.82,
    "avg_latency_sec": 4.1,
    "last_reward": 1.5
  }
}

Notes:

capabilities_summary comes from the agent’s own describe_capabilities().

performance is updated by RewardEngine / RouterLearner and the telemetry pipeline.

safety_profile matters to Gatekeeper and Planner when picking agents under certain policies.

5. Core Registry Operations

The Registry needs to expose (to Planner, CuratorAgent, CodeGeneratorAgent, etc.) a small API.

5.1 register_agent(replica_info)

Called when:

a hand-written agent is loaded at boot,

OR CodeGeneratorAgent creates a new agent file and loader.py dynamically imports it.

This method:

Adds the replica to the in-memory registry.

Persists to state/registry_state.json.

Logs a society memory entry:

[timestamp] Registered new agent BackupAgent_immediate_v5 (role=BackupAgent, traits=strategy=immediate_after_index).

Validation requirements:

agent_id must be unique.

role must be provided.

capabilities_summary must be provided.

Must attach instinct templates.

Must start with known-safe status: "active" or "quarantined" depending on safety.

5.2 update_performance(agent_id, reward_delta, success, latency_sec, escalated)

Called after a task has been attempted and logged in telemetry.

This updates:

success_count, failure_count

avg_reward, last_reward

avg_latency_sec

escalation_count

last_active_at

This gives RouterLearner better routing data later.

5.3 list_candidates(role=None, required_traits=None, policy_context=None)

Planner calls this to get all viable candidates for a task.

Behavior:

Return only "active" replicas.

Optionally filter by role (e.g. "BackupAgent").

Optionally filter by required_traits, like {"strategy": "immediate_after_index"}.

Optionally filter out replicas that violate current safety or policy context (e.g. user disabled network; candidate needs network).

policy_context can include dynamic constraints like:

{
  "network_allowed": false,
  "sensitivity": "high"
}


So if you’re trying to process very sensitive data, Planner will avoid replicas whose safety_profile includes "needs_network": true.

5.4 quarantine(agent_id, reason)

Used by CuratorAgent or GatekeeperAgent if a replica behaves suspiciously (e.g., repeatedly tries disallowed actions).

Sets:

"status": "quarantined"

logs to society memory:

[timestamp] Quarantined BackupAgent_batch_v2: repeatedly attempted network upload while policy.network.allow_external_requests=false.

Quarantined agents are not routed work by Planner.

5.5 retire(agent_id, reason)

Used by CuratorAgent to deprecate a replica that is consistently underperforming or obsolete.

Sets status to "retired".

Sets alive=False.

Sets retired_at timestamp and retire_reason.

Writes a final retirement block into that agent replica’s memory Markdown:

## [2025-11-02T22:10Z] RETIREMENT
- I am BackupAgent_batch_v2.
- Reason for retirement: lower user satisfaction, slower backup, high escalation frequency.
- Lessons: user prefers immediate confirmation backups.


Also logs to society memory for future reference.

Planner will exclude retired replicas from routing.

5.6 get_agent(agent_id)

Return the full metadata for one replica.
Used by:

Planner (for explainability),

ReflectionAgent (for summarizing the day),

CodeGeneratorAgent (to build better descendants).

6. How Planner Uses the Registry

Planner uses the Registry in three main ways:

Capability lookup:
“I need an agent that can ‘ingest new books from Drive’ → who says they can do that?”

Replica selection:
Multiple replicas might claim the same ability. Planner asks RouterLearner + Registry for the best candidate.

Exploration / exploitation balance:
Planner can route some % of tasks to high-performing replicas (exploit), and some to newer replicas (explore) to gather more reward data.

This is where the evolution happens.

7. How Curator Uses the Registry

CuratorAgent is the “gardener” of the society.

It:

Reads performance signals from Registry.

Quarantines risky replicas.

Retires low-reward replicas.

Promotes highly rewarding behavioral traits (e.g. concise responses, immediate backups) back into:

preferences.json (global defaults),

policies.json (approved strategies),

and future replicas (through CodeGeneratorAgent’s prompts / archetypes).

CuratorAgent can also tell CodeGeneratorAgent:

“Clone BackupAgent_immediate_v5’s behavior and instincts, but specialize it for fiction instead of geopolitics.”

That’s replication-with-mutation.

8. How CodeGeneratorAgent Uses the Registry

When Planner says “we’re missing an agent for X,” CodeGeneratorAgent will:

Read Registry’s current replicas for similar roles.

Copy a successful replica’s traits, instincts, and capabilities_summary as training hints.

Generate a new agent under agents/dynamic/, using the appropriate archetype.

Register it into the Registry.

The Registry therefore acts like:

a live catalog,

an R&D lab notebook,

and a breeding ground for new replicas.

9. Persistence

The Registry must persist across restarts to maintain continuity and allow long-term learning.

We store registry state in state/registry_state.json.

Requirements:

On startup:

Load registry_state.json into memory.

Mark all "status": "active" replicas as alive=True.

Mark "quarantined" replicas as alive=True but "active"=False for routing.

Mark "retired" replicas as alive=False.

On runtime changes (register, quarantine, retire, performance update):

Update in-memory view and write to disk.

Optionally append an event to memory/society/<YYYY-MM-DD>.md.

This gives you both machine-readable continuity and human-readable accountability.

10. Safety and Policy Integration

Registry data is also used to guard against unsafe routing.

Two critical checks:

10.1 Policy compatibility

Before Planner routes a task, it asks:

“Would this replica’s declared behavior violate any active policy?”

Example:

If policies.network.allow_external_requests=false and a replica’s safety_profile.needs_network=true, that replica cannot be chosen.

10.2 Trustworthiness

Planner and Gatekeeper can look at:

escalation_count and failure_count to measure instability,

avg_reward to measure usefulness,

quarantined status before routing high-risk tasks.

This keeps untrusted replicas away from sensitive or irreversible actions.

11. Registry and Memory

When:

a replica is registered,

quarantined,

retires,

or becomes star-performer,

the Registry (through CuratorAgent or Planner/ReflectionAgent) writes a short summary to society memory.

Example addition to memory/society/2025-11-02.md:

## [2025-11-02T20:15Z] Replica Lifecycle
- Registered BackupAgent_immediate_v5 (strategy=immediate_after_index). Early performance good.
- Quarantined BackupAgent_batch_v2 due to repeated policy friction on backup timing.
- Planner prefers immediate_v5 for geopolitics category due to higher reward and fewer escalations.


This gives you a readable evolutionary timeline.

12. Summary of Required Registry API

At minimum, core/registry.py must expose:

register_agent(replica_info: dict) -> None

update_performance(agent_id: str, reward_delta: float, success: bool, latency_sec: float, escalated: bool) -> None

list_candidates(role: str = None, required_traits: dict = None, policy_context: dict = None) -> list[dict]

quarantine(agent_id: str, reason: str) -> None

retire(agent_id: str, reason: str) -> None

get_agent(agent_id: str) -> dict

Optional but nice:

all_active_roles() -> list[str]

all_active_replicas(role: str) -> list[dict]

13. Why this matters

The Registry is how the Planner knows “who can help.”

The Registry is how Curator knows “who should keep existing.”

The Registry is how CodeGenerator knows “who should be cloned.”

The Registry is how RouterLearner knows “who is performing well.”

The Registry is how Gatekeeper and policy enforcement avoid routing unsafe actors into unsafe work.

It’s literally the society’s living census.