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
