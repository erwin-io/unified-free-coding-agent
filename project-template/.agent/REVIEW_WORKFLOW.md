# Temporary Tech Lead review workflow

1. Agent works locally on agent/TASK-ID branch, not on main.
2. Agent writes a handoff and executes project tests.
3. Deterministic supervisor independently runs validation and writes evidence.
4. Owner uploads .agent/TECH_LEAD_REVIEW.md to ChatGPT Tech Lead.
5. Tech Lead returns APPROVED / CHANGES REQUIRED / BLOCKED with evidence.
6. Owner explicitly accepts or requests changes.
7. GitHub branch publication, PR and merge are separate authorized actions.

For interactive sessions generate packet using RUN-REVIEW.bat.
The packet only summarizes Git changes. Provide actual diff or PR for review.
Never upload private keys, .env, credentials or uploaded user data.
