# Architecture — Unified Free Coding Agent

## Responsibility boundaries
1. VS Code/OpenCode owns interactive editor sessions, tool calls and source edits.
2. Local FastAPI router owns the stable auto-coder model endpoint, free-route
   allowlist, per-provider metadata counters, utilization warnings and failover.
3. Persistent SQLite supervisor owns task queue, retry policy, daily task cap,
   owner review state, capacity polling and optional owner notification.
4. Each target repository owns approved backlog, validation scripts, policy, actual source,
   Git diff and model-readable handoff documents.
5. Models own none of the above. They are disposable inference workers.

## Free routing lifecycle
- OpenCode sends an OpenAI-compatible request to 127.0.0.1:4030/v1.
- Gateway selects an eligible configured free model based on request count,
  conservative context estimate, and 70/85/95 percent warning thresholds.
- For a 429 or selected 5xx before stream output, a different eligible model
  may be tried. After a stream begins, there is no automatic replay because
  tool-call fragments may already have reached the client.
- When all configured providers are temporarily unavailable, return a
  structured 503 error. The supervisor saves task state and schedules retry.
- Providers may impose unpublished shared upstream limits or change free terms.
  Local request accounting is a forecast, NOT an authoritative provider quota.

## Task state machine
queued -> running -> ready_for_review -> completed
queued -> waiting_capacity -> running
running -> awaiting_owner -> queued (owner decision)
running -> waiting_capacity (process/network interruption)
running -> awaiting_owner (failed acceptance or max attempts)

The supervisor state file is .agent/SUPERVISOR_STATE.md. Agents maintain their
own .agent/HANDOFF.md, so supervisor updates cannot replace agent notes.
The supervisor imports Status: approved backlog entries from
PROJECT_PATH/.agent/BACKLOG.md, de-duplicated by project and stable TASK-ID.
No initial task is read from .env. Independently verified project checks come
from existing test scripts or an optional .agent/validation.json owned by the
project. Missing checks do not pass; command outputs/exit codes are recorded
in .agent/TEST_EVIDENCE.md. This is terminal-based execution, not serial-port
testing (unless the project explicitly needs serial hardware).
Git and actual test results are more authoritative than model-generated prose.

## Owner communication
SMTP owner reports use explicit credentials in local ignored .env.
The service never forwards source code or secrets in owner email.
Owner guidance is supplied through the local decide CLI and saved into
.agent/OWNER_DIRECTION.md. Automatic email reply parsing is NOT implemented.

## Acceptance strategy
Run offline unit tests, then verify a live response from each intended free
provider separately, one controlled code modification in a test project,
quota-429 fallback with mocks, interrupted run recovery, owner approval,
and unattended runner only under a restricted Windows user or sandbox.

## Security principles
- No external binding on the router; no Git push/deployment permissions.
- No credentials in Git; no agent access to .env.
- Never let free cloud providers see proprietary code without authorization.
- Free inference is best effort; no unlimited quota or uninterrupted SLA.
