# Project engineering agent rules
Read .agent/ARCHITECTURE.md, POLICY.md, DECISIONS.md, BACKLOG.md,
TEST_EVIDENCE.md and HANDOFF.md. Approved tasks live in the project backlog.
Discover and run real tests through terminal scripts; preserve exit codes.
The supervisor independently reruns applicable checks before owner review.
Preserve existing project contracts. Never claim completion without verified test evidence.
Detect the target stack and load the relevant skill (node-web-development,
angular-node-development, micropython-firmware, cpp-development).
Never flash or erase a microcontroller, choose a physical pin, or change
board/toolchain settings without an explicit owner-approved board specification.
Never reveal secrets, push, merge, deploy or touch production resources.
Inspect git status and git diff after model changes.
If blocked, write a specific question to .agent/OWNER_REQUEST.md and STOP.

## Owner-controlled application processes
When the owner asks to stop or restart a local development application, identify
the project and port and inspect the actual running process. Do not kill every
node.exe or python.exe process, do not call taskkill /IM, and never stop the
AI router on port 4030. For the managed Node demo, use the following
repository-owned command (UNIFIED_AGENT_ROOT is set by the launcher):
powershell -ExecutionPolicy Bypass -File "$env:UNIFIED_AGENT_ROOT\run.ps1" -Mode status-app
powershell -ExecutionPolicy Bypass -File "$env:UNIFIED_AGENT_ROOT\run.ps1" -Mode stop-app
powershell -ExecutionPolicy Bypass -File "$env:UNIFIED_AGENT_ROOT\run.ps1" -Mode start-app
Only use -AllowUntracked with explicit owner authorization after inspecting
the PID/command line, and only for the requested project on port 3000.
These actions never modify or delete project source files.

## Project-level review checkpoint
Read and honor .agent/CHECKLIST.md, .agent/BACKLOG.md and .agent/SPRINT.md.
Approved backlog entries are the only unattended task source. For unattended
work, the supervisor creates a dedicated agent/TASK-ID Git branch; never edit
main directly in autonomous mode. Complete only the current approved scope.
Record actual test exit codes and implementation decisions in HANDOFF.md.
Never change the status to Tech Lead APPROVED yourself. Stop for review at
ready_for_review. No direct push, PR publication, merge, deployment or
production migrations without current, specific owner approval.
