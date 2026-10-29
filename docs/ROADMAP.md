# Delivery status

## Implemented in repository (local tests still required on your PC)
- Free-only proxy with quota warnings, SQLite counters and pre-stream failover.
- Single-agent SQLite task queue and per-project Markdown handoffs.
- Bounded retries, configured acceptance test and owner-review gate.
- Optional SMTP owner notifications.
- OpenCode 2 configuration, Windows launcher, unit tests and CI.

## Not implemented or not yet verified
- Live credentials and provider integration; actual zero-cost eligibility checks.
- Per-token streaming accounting and upstream quota reconciliation.
- Automatic tool-level OpenCode checkpoint hook at each edit.
- Reading owner email replies and authenticated approval links.
- Fully calendar-aware scrum sprint scheduling, visual dashboard.
- Multi-agent parallel execution and independent sandboxed runner.
