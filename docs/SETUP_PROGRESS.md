# Setup progress (source of truth)

## Repository-side
- [x] Main branch contains router, supervisor, Windows launcher and local project template.
- [x] Provider aliases locked to documented free routes.
- [x] SQLite request counts, capacity warnings and pre-stream failover.
- [x] Task queue, bounded retries, owner review, project-specific handoff files.
- [x] OpenCode 2 integration configuration and editor extension bootstrap.
- [x] Node.js full-stack example UI, in-memory API and four automated tests.
- [x] Windows demo project scaffold, local Git baseline and health-check launch script.
- [x] Unit-test/compile workflow configured on GitHub Actions.

## Owner-side (not verified; do not mark complete without evidence)
- [ ] Clone repository locally and verify main HEAD.
- [ ] Install Python 3.10+, Node.js/npm, Git, VS Code (VS Code optional).
- [ ] Create .env from .env.example and enter allowed provider keys.
- [ ] Select PROJECT_PATH pointing to your local Git repository.
- [ ] Leave AUTONOMOUS_ENABLED=false initially.
- [ ] Execute powershell -ExecutionPolicy Bypass -File .\run.ps1
- [ ] Verify router health, provider response and successful OpenCode tool call.
- [ ] Approve a task in PROJECT_PATH/.agent/BACKLOG.md and confirm its import.
- [ ] Verify automatic test discovery and .agent/TEST_EVIDENCE.md outputs.
- [ ] Verify git diff, checkpoint, task recovery and owner email if enabled.
- [ ] Only after safety review: authorize autonomous sandboxed execution.

## Future development
- [ ] Real provider account quota reconciliation.
- [ ] Exact stream token consumption and durable every-tool checkpoint hook.
- [ ] Secure email-reply approval channel and scheduled sprint/calendar policies.
- [ ] OS-level sandboxing with a restricted test environment.

Always distinguish unit-test success from real-provider, Windows and unattended
acceptance. Never declare setup complete until owner-side validation passes.
