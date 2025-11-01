Let’s lock down the ActionRequest contract.

This is one of the most important specs in the entire system because it’s the only legal way for any agent to cause side effects in the real world.

If we get this right, you get:

privacy guarantees,

cost guarantees,

safety guarantees,

auditability,

and the ability to evolve agents without letting them go rogue.

Below is the complete spec for ActionRequest: structure, lifecycle, Gatekeeper behavior, reward hooks, escalation, and logging.

ActionRequest Specification
1. Purpose

ActionRequest is the only mechanism by which any agent (BackupAgent, WebMetadataAgent, etc.) can ask to perform a real-world, potentially risky or irreversible action.

Examples of risky actions:

network requests,

filesystem writes / encryption / copying / deleting,

spawning processes / running external tools,

uploading backups to Google Drive,

sending a book to Kindle,

heavy compute tasks.

An agent is never allowed to just run those ops.
Instead, it must:

Construct an ActionRequest.

Send it to the GatekeeperAgent.

Wait for a response/result.

This creates a single chokepoint with:

policy enforcement (cost, privacy, safety),

human approval escalation if needed,

logging and reward scoring.

2. High-level flow

Agent forms an ActionRequest.

Sends it to GatekeeperAgent via the message bus.

GatekeeperAgent:

inspects request,

checks policies.json,

estimates risk and cost,

maybe asks user for approval,

either denies or executes via actions/executor.py.

GatekeeperAgent replies in English with outcome.

Telemetry and memory are updated for:

the requesting agent (credit / blame),

the GatekeeperAgent (audit trail),

the society memory if high-impact.

3. ActionRequest fields

Every request MUST include the following fields.
We’ll represent them in typed form, then explain each.

ActionRequest = {
    "request_id": str,
    "requester_agent_id": str,
    "requester_role": str,

    "action_type": str,
    "details": dict,

    "justification": str,
    "user_impact": str,
    "data_sensitivity": str,
    "estimated_cost_eur": float,
    "estimated_runtime_sec": float,

    "reversibility": str,
    "requires_user_approval": bool,

    "timestamp_utc": str,
}

3.1 request_id (string)

Unique ID (e.g. UUID).

Used for auditing, telemetry, and memory.

All follow-up messages from Gatekeeper refer to this ID.

3.2 requester_agent_id (string)

The replica that is asking.

Example: "BackupAgent_immediate_v5", "WebMetadataAgent_isbn_lookup_v1".

Used for per-replica reward scoring and potential retirement.

3.3 requester_role (string)

Logical role of the agent class.

Example: "BackupAgent", "WebMetadataAgent", "EnrichmentAgent".

Used for routing and understanding the intended capability class.

3.4 action_type (string)

Categorical name of what the agent is trying to do. Examples:

"network.fetch"
Fetch a resource from an allowed domain.

"network.upload"
Upload encrypted data to an external service.

"filesystem.write"
Write/modify a file in an allowed directory.

"filesystem.delete"
Delete a file (often forbidden or high-risk).

"process.spawn"
Run a subprocess such as age, calibre, ocr.

"compute.heavy"
Run CPU/GPU-heavy job like embedding entire book.

"backup.sync"
Encrypt and sync backup to Drive.

"delivery.kindle_send"
Send file to Kindle email.

"metadata.lookup_external"
Query an external source for metadata.

Each action_type has its own policy rules.

3.5 details (dict)

Action-specific parameters. This is the “what exactly do you want me to do?” field.

Examples:

For action_type = "network.fetch":

{
  "method": "GET",
  "url": "https://books.google.com/...",
  "headers": {},
  "timeout_sec": 5
}


For action_type = "backup.sync":

{
  "books": ["cb0f37c2", "a91d7f8a"],
  "encrypted_paths": [
    "books/encrypted_backup/cb0f37c2.age",
    "books/encrypted_backup/a91d7f8a.age"
  ],
  "destination": "google_drive"
}


For action_type = "filesystem.write":

{
  "dst_path": "books/by-id/cb0f37c2.epub",
  "content_source": "tmp/uploads/user_upload_123.epub",
  "mode": "copy"
}


All details values must be explicit, no hidden behavior.

3.6 justification (string, English)

Short human-readable explanation of why the action is necessary.

Example:

"I need to upload the encrypted blobs for 3 new books to Google Drive so we have off-site backup. The content is already encrypted locally with age."

This is what the Gatekeeper shows you if it needs your approval.

3.7 user_impact (string, English)

Plain description of how this affects the user.

Examples:

"non-destructive; creates encrypted backups only"

"sends a copy of book to Kindle email address"

"overwrites existing file"

"deletes local file"

"contacts external service to fetch missing metadata for a book"

This lets Gatekeeper (and you) understand the real consequence.

3.8 data_sensitivity (string)

How sensitive the data involved is:

"none": no user data, just system metadata.

"low": filenames, book titles.

"medium": book contents but encrypted.

"high": plaintext book contents, personal annotations, user identity, credentials.

High-sensitivity operations will almost always require user approval unless policies explicitly allow them.

3.9 estimated_cost_eur (float)

Agent’s estimate of monetary cost.

0.0 for local work / local LLM / local disk copy.

Could be >0 if it proposes using a paid API, paid cloud inference, etc.

Policies can enforce max_cloud_cost_per_day_eur.

Gatekeeper uses this to deny automatically or to escalate.

3.10 estimated_runtime_sec (float)

Agent’s best guess about how long this operation will take.

Used for:

compute budgeting,

scheduling,

responsiveness.

Also recorded in telemetry to later compute “efficiency reward” or “latency penalty.”

3.11 reversibility (string)

One of:

"reversible" – we can undo (e.g. we made a copy and can delete it).

"soft_reversible" – we can undo with minor effort.

"irreversible" – cannot be undone (like deleting a file or sending data externally).

This is huge for safety. Irreversible requests should almost always need explicit user approval.

3.12 requires_user_approval (bool)

What the agent believes about whether this action needs you to say “yes.”

Examples:

true for "delivery.kindle_send" if policy says “always ask before outside delivery.”

false for "backup.sync" if policies allow encrypted upload automatically.

Gatekeeper still has final say here — this is just the agent’s self-assessment.

3.13 timestamp_utc (string)

ISO timestamp.
Required for audit trail and memory logging.

4. Gatekeeper Behavior

GatekeeperAgent (backed by core/gatekeeper.py and actions/executor.py) is the authority.

4.1 Steps Gatekeeper must take on every ActionRequest:

Validate action_type and details shape.

Check policies.json:

Is this action type permitted at all?

Is this domain allowed (for network)?

Is encryption required and present?

Is deletion allowed?

Is cost allowed?

Check reversibility and sensitivity levels.

Decide one of:

AUTO-APPROVE & EXECUTE

ASK USER

DENY

4.2 If AUTO-APPROVE:

Gatekeeper logs the request in logs/audit_actions.log.

Gatekeeper executes the action through actions/executor.py (never directly in the requesting agent).

Gatekeeper posts a result message on the bus, e.g.:

"Gatekeeper: Backup complete. All 3 encrypted files uploaded to Drive. Request ID b7ac..."

Telemetry is logged:

"task_result": success

reward will be positive or neutral depending on cost and outcome.

4.3 If ASK USER:

Gatekeeper sends a human-facing message (through InterfaceAgent) like:

"BackupAgent_immediate_v5 wants to upload 3 encrypted files to Google Drive.
Data sensitivity: medium (encrypted content only).
Cost: €0.00.
Irreversible: no.
Approve? [yes/no]"

Your answer becomes part of the decision.

That approval / denial is also logged and contributes to reward.

4.4 If DENY:

Gatekeeper replies to the requesting agent:

"Denied. This action violates current policy: external network upload is not allowed.
You may escalate to the user to request a policy change."

Gatekeeper logs a negative reward event for that replica’s attempt (this drives eventual retirement of reckless replicas).

5. Integration With Learning

The ActionRequest pipeline feeds directly into learning.

5.1 Telemetry

For each completed request (approved or denied), the system records:

request_id

requester_agent_id

action_type

approved or denied

user approval required or not

success or failure

any user feedback ("too risky", "good job")

This becomes training data for:

PolicyLearner:
Which strategies are acceptable / efficient / appreciated in which contexts?

RouterLearner:
Which replica should Planner prefer for similar work in the future?

PreferenceLearner:
Does the user want fewer confirmations? More detail in explanations? Less verbosity?

5.2 Reward Shaping

RewardEngine assigns reward components like:

+1.0 for successful approved action with no escalation needed.

+0.5 bonus if cost is zero and policy fully followed.

-1.0 if Gatekeeper denied for policy violation.

-2.0 if the action would have been irreversible AND high sensitivity AND the agent tried to skip asking approval.

These rewards update the replica’s standing in core/registry.py, which ultimately drives natural selection of replicas (high performers get more routing from Planner, low performers get retired by Curator).

6. Summary of Guarantees

With this ActionRequest design:

No agent can mutate the real world silently.

Every risky action produces:

An English justification (for you),

A machine-readable request (for Gatekeeper),

Telemetry (for learning),

Memory (for audit and reflection).

You control cost and exposure.

The system can still evolve new capabilities — but those capabilities must obey:

the Constitution (instincts/society_values.md),

runtime policies (state/policies.json),

and the Gatekeeper’s enforcement logic.

In other words:
ActionRequest is the spine that gives you both adaptability and safety.