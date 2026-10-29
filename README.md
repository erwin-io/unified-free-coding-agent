# Unified Free Coding Agent

A Windows-first, free-cloud-only coding gateway and supervisor that works with OpenCode 2.
Repository: https://github.com/erwin-io/unified-free-coding-agent

## Quick start: your only required actions

1. Register for any free model providers you want (Kilo anonymous may work without registration).
   See docs/ACCOUNTS.md.
2. Clone the repository and configure the local environment:
   
       git clone https://github.com/erwin-io/unified-free-coding-agent.git
       cd unified-free-coding-agent
       Copy-Item .env.example .env
       notepad .env

   Set PROJECT_PATH to the absolute Windows path of the Git repo you want to edit.
   Enter GEMINI_API_KEY and/or OPENROUTER_API_KEY (optional KILO_API_KEY).
   You can test with KILO_ENABLED=true and no Kilo key. Never commit .env.
3. In PowerShell, run the single launcher command:

       powershell -ExecutionPolicy Bypass -File .\run.ps1

   It creates a Python virtual environment, installs requirements, runs local tests,
   installs official OpenCode 2 if missing, optionally installs the official VS Code
   beta integration if the code command is on PATH, starts the local model router, initializes
   project agent notes without overwriting existing files, and opens OpenCode.
   No GPU or paid API is required. You need Python 3.10+, Node.js/npm, Git and internet.

## Accounts / env fields

| Variable | Required? | Meaning |
| --- | --- | --- |
| FREE_ROUTER_KEY | Yes (local default) | Local loopback auth key, not a provider key |
| KILO_ENABLED | Yes | Enable Kilo Auto Free; anonymous supported |
| KILO_API_KEY | Optional | Authenticated Kilo gateway |
| GEMINI_API_KEY | Optional | Google AI Studio free-tier project key |
| OPENROUTER_API_KEY | Optional | OpenRouter free-route key |
| PROJECT_PATH | Recommended | Absolute path to local Git project |
| INITIAL_TASK | Optional | First task; seeded only once on project initialization |
| TEST_COMMAND | Required for verified task completion | Acceptance command for chosen project |
| AUTONOMOUS_ENABLED | No, defaults false | Enables unattended worker |
| AUTONOMOUS_AUTO_APPROVE | No, defaults false | Allow headless OpenCode tools in a TEST repository only |
| EMAIL_ENABLED, OWNER_EMAIL, SMTP_* | Optional | Sends owner notifications via SMTP |

Key registration: docs/ACCOUNTS.md. Read docs/SECURITY.md before unattended operation.

## Runtime controls

    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode doctor
    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode status
    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode test
    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode once

Task management after setup:

    .\.venv\Scripts\python.exe -m automation.cli add "Implement feature X, acceptance tests Y" --title "Feature X"
    .\.venv\Scripts\python.exe -m automation.cli status
    .\.venv\Scripts\python.exe -m automation.cli decide 1 "Approved approach B; keep API contract unchanged"

For unattended execution, set AUTONOMOUS_ENABLED=true and
AUTONOMOUS_AUTO_APPROVE=true only in a disposable test repo you control.
The launcher then starts the local supervisor. One active coding agent at a time.
The supervisor retries only a bounded number of times and never pushes to GitHub.

## How model switching works

OpenCode always sees unified/auto-coder. This local gateway routes to:
- Kilo Gateway: kilo-auto/free, available without credentials on eligible anonymous access.
- Gemini API: gemini-2.5-flash, only when you provide a free-tier project key.
- OpenRouter API: openrouter/free, only when you provide an API key.

The router records request counts and warnings, and uses an alternate provider after a
pre-stream 429/5xx. Streams that already started are NEVER blindly replayed. A model
cannot reliably continue mid-token. OpenCode history and .agent/HANDOFF.md preserve
the verified task state for the next request, independent of model identity.

When every free cloud endpoint is unavailable, the supervisor saves a waiting task
and checks again later. No inference or coding progress is possible without capacity.
The local supervisor, task database and optional email notifications can still run.
No zero-outage, identical-model-quality or free-unlimited-use guarantee is made.

## Autonomous task acceptance

The supervisor creates .agent/HANDOFF.md based on Git state.
When an OpenCode run ends, the operator-configured TEST_COMMAND runs locally.
Only an exit code of 0 on the task process and acceptance command changes status to
ready_for_review, not completed. The owner reviews the diff; no automatic deployment.
If uncertain, the agent can put a question in .agent/OWNER_REQUEST.md and send an
optional email; directions are entered through the local CLI, not by parsing email.

The supervisor is single-machine/single-worker; avoid launching duplicate workers.
Local runtime files live under .agent-runtime (ignored by Git).
Logs are kept locally and can contain model text: protect your workstation.

## Project layout

- router: free model gateway and metadata usage store
- automation: persistent backlog, single-agent runner, owner notifications
- project-template/.agent: shared notes, contracts and handoff templates
- .opencode: reviewer role and handoff skill
- run.ps1: Windows one-command setup and launcher
- tests: offline unit tests
- .github/workflows/ci.yml: compile + unit tests

## Current limits

A working source baseline does not establish real-provider compatibility.
No owner-email reply parser, exact token-level streaming accounting, fully automatic
per-tool checkpoints, or calendar-aligned sprint scheduling is implemented.
See docs/ROADMAP.md for truthful status. Run in a nonconfidential repository first.
