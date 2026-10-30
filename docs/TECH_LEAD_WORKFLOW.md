# Tech Lead Review - manual ChatGPT handoff

This is a temporary human-in-the-loop workflow. It has no dependency on the
ChatGPT conversation connecting directly to the developer machine.

## Per-project files
- .agent/BACKLOG.md is the only executable backlog source (Status: approved).
- .agent/CHECKLIST.md is the owner-maintained scope/acceptance checklist.
- .agent/SPRINT.md stores human priority and phase planning.
- .agent/HANDOFF.md is implementation notes from coding agent.
- .agent/TEST_EVIDENCE.md contains independently observed checks.
- .agent/TECH_LEAD_REVIEW.md is the deterministic review summary.

## Sequence
1. Owner adds approved task to BACKLOG.md, noting checklist ID/criteria.
2. With unattended mode explicitly enabled for a disposable sandbox, the
   worker creates an agent/TASK-ID branch and works on that task only.
3. If tests pass, worker generates TECH_LEAD_REVIEW.md and stops. It does
   not move to next task while a local review is pending.
4. Owner runs RUN-REVIEW.bat if working in an interactive OpenCode session.
5. Owner uploads .agent/TECH_LEAD_REVIEW.md and actual Git diff or PR into
   a ChatGPT Tech Lead chat. The review is advisory until owner accepts it.
6. For an autonomous task, owner runs from agent repository:
   .\.venv\Scripts\python.exe -m automation.cli decide ID "APPROVED"
   or: .\.venv\Scripts\python.exe -m automation.cli decide ID "CHANGES REQUIRED: add upload API tests"
   or: .\.venv\Scripts\python.exe -m automation.cli decide ID "BLOCKED"
7. APPROVED marks the queue item complete, but neither publishes a PR
   nor merges the feature branch. Owner still performs GitHub review/merge.
8. Before starting another unattended task, return to a clean reviewed
   main branch after a manual merge. Do not reset or discard uncommitted work.

## Copy into the ChatGPT Tech Lead chat

Act as the independent Tech Lead reviewer. Review the uploaded
TECH_LEAD_REVIEW.md plus source code diff and project checklist.
Do not infer feature correctness from passing old tests. Inspect actual
new/modified code, API compatibility, security, test coverage and CI.
Return APPROVED only with sufficient proof; otherwise return CHANGES REQUIRED
with exact filenames and tests, or BLOCKED with a concrete reason.
Do not merge any branch or change production data automatically.
Wait for the project owner's decision before a GitHub merge.

## Honest limitations
- A report with Git status and filenames alone is NOT a full code review.
- The ChatGPT connector does not connect OpenCode to GitHub.
- No authenticated reviewer replies or secure approval links are implemented.
- The supervisor can retry approved backlog tasks as capacity recovers, but
  cannot guarantee infinite inference or continuation during an offline PC.
- Daily task count is currently a rolling 24-hour cap, not a scrum scheduler.
