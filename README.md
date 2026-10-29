# Unified Free Coding Agent

A Windows-first, free-cloud-only coding gateway and supervisor that works with OpenCode 2.
It now includes safe project scaffolding and stack-specific skills for Node.js + HTML/CSS/JS,
Angular + Node.js, MicroPython and C++/CMake. See docs/STACKS.md.
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
   If PROJECT_PATH points to C:\Development\test-nodejs-web-app and that folder
   does not yet contain a local Git repository, the launcher safely bootstraps a
   working full-stack Node.js demo into an empty directory, executes tests, creates
   a local Git baseline, and opens UI + API at http://127.0.0.1:3000.
   If a previous bootstrap copied only part of the demo, the script recognizes
   matching template files, completes the missing files, and resumes Git init.
   Unrelated existing files (such as filestructure.txt) are preserved, not staged
   or overwritten. Existing demo files that differ from the template still block
   setup, so the script never silently replaces user source code.
   No GPU or paid API is required. You need Python 3.10+, Node.js/npm, Git and internet.

## Accounts / env fields

| Variable | Required? | Meaning |
| --- | --- | --- |
| FREE_ROUTER_KEY | Yes (local default) | Local loopback auth key, not a provider key |
| KILO_ENABLED | Yes | Enable Kilo Auto Free; anonymous supported |
| KILO_API_KEY | Optional | Authenticated Kilo gateway |
| GEMINI_API_KEY | Optional | Google AI Studio free-tier project key |
| OPENROUTER_API_KEY | Optional | OpenRouter free-route key |
| PROJECT_PATH | Required for demo | C:\Development\test-nodejs-web-app |
| PROJECT_STACK | New projects | auto, node-web, angular-node, micropython, cpp |
| AUTONOMOUS_ENABLED | No, defaults false | Enables unattended worker |
| AUTONOMOUS_AUTO_APPROVE | No, defaults false | Allow headless OpenCode tools in a TEST repository only |
| EMAIL_ENABLED, OWNER_EMAIL, SMTP_* | Optional | Sends owner notifications via SMTP |

Key registration: docs/ACCOUNTS.md. Read docs/SECURITY.md before unattended operation.

## Node demo server health and port conflicts

The Windows launcher starts the Node demo through `scripts/ensure-node-demo.ps1`.
It reuses a healthy server on port 3000, refuses to stop an unrelated service,
and captures fresh Node stdout/stderr into `.agent-runtime/demo-*.log`.
If the backend is broken (for example after an incomplete code edit), it shows
the Node error and **continues opening OpenCode** so the agent can repair the
project. The launcher never resets project files, Git, or API credentials.
A passing `npm test` does not guarantee that a live server can start.

If the browser cannot load the demo, inspect the warning and the latest
`demo-*.err.log` file in `.agent-runtime`. Use
`Get-NetTCPConnection -State Listen -LocalPort 3000` to inspect a port conflict.
Do not kill unknown Node processes.

## Runtime controls

    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode doctor
    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode status
    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode test
    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode once

Project tasks are defined in PROJECT_PATH/.agent/BACKLOG.md, which the launcher
creates if missing. Edit a TASK-001 section with the title, description and
acceptance criteria. Change Status: draft to Status: approved when YOU have
authorized execution; the supervisor imports that task automatically.
Interactive tasks can also be given directly in OpenCode, without a backlog entry.

Tests are discovered from existing project commands rather than an environment
variable: npm scripts (test, typecheck, lint), Go, Rust, .NET, Java, or Python
project tests. If your project needs custom checks, create
PROJECT_PATH/.agent/validation.json with the following JSON:

    {"commands":[["npm","run","test"],["npm","run","lint"]]}

Each command is executed with subprocess argv, no shell=True. The agent can
run additional tests via terminal; the supervisor independently reruns the
discovered commands and stores exit codes in .agent/TEST_EVIDENCE.md.
If no usable tests exist, it pauses for owner review instead of passing.

Optional CLI task management:

    .\.venv\Scripts\python.exe -m automation.cli add "Implement feature X, acceptance tests Y" --title "Feature X"
    .\.venv\Scripts\python.exe -m automation.cli status
    .\.venv\Scripts\python.exe -m automation.cli decide 1 "Approved approach B; keep API contract unchanged"

For a NEW project, set PROJECT_PATH and PROJECT_STACK in .env, then run the
same .\run.ps1 command. For one-time overrides, run:
    powershell -ExecutionPolicy Bypass -File .\run.ps1 -Stack angular-node

Angular v22 needs Node 22.22.3+, Node 24.15+ or Node 26+.
MicroPython hardware uploads require explicit mpremote/serial approval.
C++ local builds require a compiler and CMake; embedded C++ requires a
board-specific toolchain such as PlatformIO. See docs/STACKS.md.

For unattended execution, set AUTONOMOUS_ENABLED=true and
AUTONOMOUS_AUTO_APPROVE=true only in a disposable test repo you control.
The launcher then starts the local supervisor. One active coding agent at a time.
The supervisor retries only a bounded number of times and never pushes to GitHub.

## Gemini 3 and coding tools

Google Gemini 3 requires thought signatures to be returned unchanged across
multi-step function calls. Our OpenCode OpenAI-compatible history may omit these
provider-specific signatures. The gateway therefore excludes direct Gemini
from tool-enabled requests (including requests with past tool-call messages).
Gemini remains available for normal text-only chat. Kilo and OpenRouter can
serve tool requests when their free endpoints are eligible. If neither has
capacity, the router returns HTTP 503 FREE_TOOL_CAPACITY_UNAVAILABLE instead
of sending a tool request to Gemini that would fail with a signature-related 400.
The task supervisor uses separate tool-capacity status for its retry decision.

This is a conservative compatibility guard, **not** a complete Gemini
thought-signature implementation. Full support requires retaining exact
provider-specific signatures in streaming and persisted tool histories.

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

The supervisor writes .agent/SUPERVISOR_STATE.md from observed Git state and keeps
agent-authored .agent/HANDOFF.md separate. After an OpenCode run, it automatically
runs discovered project validation commands (or .agent/validation.json commands).
Only successful independent checks and a successful agent process change status to
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
- templates/: Angular + Node, MicroPython and C++ starters
- automation/scaffold.py: reusable non-overwriting project initializer
- docs/STACKS.md: prerequisites, supported stacks, hardware limitations
- .opencode: reviewer role and handoff skill
- run.ps1: Windows one-command setup and launcher
- tests: offline unit tests
- .github/workflows/ci.yml: compile + unit tests

## Current limits

A working source baseline does not establish real-provider compatibility.
No owner-email reply parser, exact token-level streaming accounting, fully automatic
per-tool checkpoints, or calendar-aligned sprint scheduling is implemented.
See docs/ROADMAP.md for truthful status. Run in a nonconfidential repository first.
