# PHASE_0_GOAL.md

## Purpose

Phase 0 is the "society boots and breathes" milestone.

This document defines:
1. What **must be true** at the end of Phase 0.
2. What **must not happen**.
3. How to **verify it from the outside** (without reading code).
4. Minimal behavior guarantees for Planner, Bus, InterfaceAgent, and Gatekeeper.

If any of these checks fail, Phase 0 is not complete.

---

## 1. High-Level Goal of Phase 0

We can start the system, it can:
- Create the core agents (PlannerAgent, GatekeeperAgent, InterfaceAgent).
- Register them in the Registry.
- Accept one user request.
- Let Planner respond in English.
- Show that response to the human (via InterfaceAgent).
- Then become idle (no infinite loops, no new messages forever).
- And we can interrupt it cleanly with SIGINT (Ctrl+C / kill -INT).

We are **not** yet ingesting books, backing up, tagging, or generating new agents.  
Phase 0 is just: *the society can wake up, talk once, and sit still safely.*

---

## 2. Runtime Behavior Requirements

### 2.1 On startup
When we run Phase 0 (`run_dev.py`), the system MUST:
- Initialize the message bus.
- Initialize the Registry (creating a fresh `state/registry_state.json` if needed).
- Initialize core agents:
  - PlannerAgent
  - GatekeeperAgent
  - InterfaceAgent
- Subscribe those agents to the bus.
- Register those agents in the Registry.
- (Optional in Phase 0) Log this registration into memory/society/<today>.md.

### 2.2 After initialization
The system MUST inject exactly one simulated user message such as:
> "Import my new books from my Android downloads."

This message MUST be routed to the Planner.

Planner MUST produce at least one human-facing response in English, e.g.:
- "I understand you want to import new books, but we do not yet have an IngestionAgent."
- "I will request that capability."

Then Planner MUST send that response as a bus Message to the recipient `"user"` (or whatever the InterfaceAgent is watching as "the human output channel").

InterfaceAgent MUST receive that message and print it (stdout or log).

### 2.3 After Planner's first response
After delivering Planner's response(s) to the user:
- **No new messages must be generated automatically.**
- The bus MUST go quiet.
- There MUST be no infinite "ack → ok → ack → ok" chatter between PlannerAgent and InterfaceAgent.
- CPU usage should drop to idle (essentially waiting).

### 2.4 Shutdown
When sent SIGINT (Ctrl+C / `kill -INT <pid>`), the system MUST:
- Stop cleanly.
- Print "Shutdown" (or equivalent) via the `except KeyboardInterrupt:` block in the wrapper.
- Exit the process.

If SIGINT does not exit in a reasonable time, Phase 0 fails.

---

## 3. "Must NOT" Rules

These are non-negotiable. If any of these occur, Phase 0 fails.

### 3.1 InterfaceAgent MUST NOT echo back to the bus in response to user-directed messages
When InterfaceAgent receives a message where `recipient == "user"`, it MUST:
- Render that message to the human (stdout / log).
- Then STOP.

It MUST NOT publish *any* new bus Message in response:
- not "delivered"
- not "ack"
- not "ok got it"
- not "Planner I told the user"
- not "User saw your message"
- nothing

This prevents infinite politeness loops.

### 3.2 Planner MUST NOT keep chatting after it has responded
Planner can send 1–2 messages to `"user"` about the request.
After that, Planner MUST NOT:
- Send follow-up messages just to acknowledge "delivery".
- Ask InterfaceAgent if the message was delivered.
- Re-explain the same thing over and over.

Planner's role in Phase 0 ends after: interpret → respond → idle.

### 3.3 bus.publish MUST NOT create a self-reinforcing loop
If `bus.publish()` takes `direct_dispatch=True` and recursively calls handlers inline, Phase 0 will break.

For Phase 0, **user-facing messages MUST NOT use direct_dispatch=True.**

If a message is addressed to `"user"`, the bus MUST deliver it in a safe way that does not immediately trigger another publish back.

### 3.4 No infinite loop
If the system produces repeating messages like:
- "Delivered"
- "Thanks"
- "Delivered"
- "Thanks"
forever, Phase 0 fails.

If the system pegs a CPU core without accepting new work, Phase 0 fails.

If KeyboardInterrupt doesn't unwind, Phase 0 fails.

---

## 4. Expected Console Transcript

Running the Phase 0 check should look approximately like this (content does not have to match literally; structure must match):

```text
[InterfaceAgent] Booting Phase 0...
[Registry] Registered agent PlannerAgent (PlannerAgent_v0) status=active
[Registry] Registered agent GatekeeperAgent (GatekeeperAgent_v0) status=active
[Registry] Registered agent InterfaceAgent (InterfaceAgent_v0) status=active

[InterfaceAgent] User said: "Import my new books from my Android downloads."
[Planner] I understand you want to import new books from your Android downloads.
[Planner] I don't currently have an IngestionAgent that can scan and import those books safely.
[Planner] I'll request a new capability for ingestion in a future step. No data has moved yet.
(idle...)
^C
Shutdown
```

Notes:
- You see Planner explain its reasoning to the user in plain English.
- You do NOT see an infinite "Delivered to user." / "Thanks." chatter.
- After Planner answers, nothing else prints automatically.
- When SIGINT is sent, the process exits and prints `Shutdown`.

---

## 5. Manual Acceptance Test (shell)

### 5.1 Clean boot and graceful shutdown test

Run this exact command:

```bash
cd /Users/akira/projects/personal_librarian && \
rm -f state/registry_state.json && \
python3 -c "
import asyncio
from run_dev import main

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('\\nShutdown')
" 2>&1 | head -40 &
DEVPID=$!
sleep 1
kill -INT $DEVPID 2>/dev/null
wait $DEVPID
```

Phase 0 passes if ALL are true:

You see some startup logs from Planner/Registry/InterfaceAgent.

You see Planner’s response to the simulated user request.

You do not see an endless stream of acknowledgments.

The process exits cleanly after SIGINT (it may print Shutdown or terminate quietly).

The command returns (the shell prompt comes back).

CPU doesn't sit spinning at 100% during that 1-second sleep.

If any one of these fails, Phase 0 is not done.


---

## 6. Code Requirements Summary (for the coding agent)

The following behaviors MUST be implemented in code to satisfy Phase 0.

### 6.1 `interface_agent.py`
**Required behavior:**
- Must subscribe to messages where `recipient == "user"`.
- When it receives such a message:
  - Print it / log it for the human.
  - DO NOT publish any reply message back to the bus automatically.
  - Return/exit the handler.

**Forbidden behavior:**
- Auto-sending acknowledgments like "Delivered to user."
- Auto-sending "Planner, I told the user".
- Auto-sending anything else in response to `recipient == "user"`.

This is a hard requirement.

### 6.2 `bus.py`
**Required behavior:**
- Must support `publish(message)` and deliver messages to subscribers.
- MUST NOT create an infinite immediate recursion between Planner and InterfaceAgent.

**Specific rule for Phase 0:**
If `message.recipient == "user"`, the bus MUST NOT call any direct or synchronous dispatch path (`direct_dispatch=True`, inline callbacks that re-enter publish, etc.).
Instead, it should route that message in a way that:
- results in InterfaceAgent handling it once,
- does not trigger another immediate publish from bus itself,
- and does not continually ping Planner again.

Effectively:
> user-directed messages go one way into InterfaceAgent and then die.

### 6.3 `run_dev.py`
**Required behavior:**
- After wiring bus + agents + registry, it should simulate one "user request" by sending a single message into the system.
- Then it should idle (e.g. by waiting on an asyncio Event, sleeping in a loop, etc.).
- It should NOT keep triggering Planner repeatedly.
- It should NOT keep injecting new user queries in a loop.

**SIGINT must terminate main():**
- When the outer script sends `kill -INT $PID`, that should raise `KeyboardInterrupt` and break out of `asyncio.run(main())`, which will print "Shutdown" (from the wrapper `except KeyboardInterrupt:`).

If SIGINT doesn't exit, Phase 0 fails.

---

## 7. Deliverables for Phase 0 to be considered complete

To mark Phase 0 complete, the coding agent MUST provide:

1. Confirmation that `interface_agent.py` satisfies §6.1 (sink-only behavior for messages to `"user"`).
2. Confirmation that `bus.py` satisfies §6.2 (no recursive direct-dispatch loops for user-facing messages).
3. Confirmation that `run_dev.py` satisfies §6.3 (exactly one simulated user request; then idle; exits cleanly on SIGINT).
4. Proof of passing the manual acceptance test in §5.1:
   - Paste the console transcript from that shell command.
   - Show that the output stops after Planner's explanation (no loops).
   - Show that "Shutdown" prints and the process ends.

Only after these 4 are provided, Phase 0 is considered passing.

---

## 8. Summary for the coding agent

**Your task as the coding agent:**
- Read this file.
- Make Phase 0 pass.
- Do not add features. Do not build ingestion. Do not build backup.
- Just make the society wake up, speak once, idle, and shut down when asked.

If the system cannot pass the acceptance test in §5.1, keep fixing `interface_agent.py`, `bus.py`, and if needed `run_dev.py` until it does.
