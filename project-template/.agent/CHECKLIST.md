# Project development checklist

This file belongs to the selected target project, not the agent repository.
Owner controls this checklist. The supervisor only executes tasks explicitly
marked Status: approved in BACKLOG.md.

## Current phase (edit for your project)
- [ ] TASK-001: Define and implement the first approved project capability
- [ ] TASK-002: Add feature-specific automated validation
- [ ] Independent tests and security checks
- [ ] Tech Lead code review and owner decision
- [ ] Owner-authorized GitHub PR and merge (never automatic)

## Review acceptance gate
- [ ] New feature-specific tests have real exit codes
- [ ] Actual code diff has been inspected
- [ ] TECH_LEAD_REVIEW.md was generated on the task branch
- [ ] Tech Lead recommended a decision; owner recorded it
- [ ] No secrets, destructive actions, or unauthorized production operations

Customize these items to match the project architecture and backlog.
