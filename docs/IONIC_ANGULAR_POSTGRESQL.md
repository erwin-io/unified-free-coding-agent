# Next full-stack experiment: Angular + Ionic + Capacitor + Node + PostgreSQL

Suggested split:
- apps/mobile: Ionic Angular + Capacitor (web, Android; iOS needs macOS/Xcode)
- services/api: Node.js TypeScript REST API (Fastify or NestJS)
- database: PostgreSQL local development only, accessed by backend, never mobile
- database tools: Prisma or Drizzle migrations, with schema and test seeds
- tests: Angular unit tests, Node API integration, database migration tests,
  Android emulator smoke tests for capacitor native bridge
- Git: branch per accepted backlog task, review packet and manual PR gate

This is a recommendation, NOT an already implemented one-click stack template.
The existing angular-node scaffold is a simpler Angular UI plus bare Node API
without Ionic, Capacitor or PostgreSQL. Start by separately verifying Ionic
CLI on Node compatible with Angular; Android Studio and Android SDK are required
for device builds. Capacitor requires native platform initialization and sync.
Database connectivity and migration must be tested against a disposable local
PostgreSQL instance; never run migrations against production without approval.

Suggested project milestones:
TASK-001 Scaffold Ionic Angular tabs PWA and run web build.
TASK-002 Add Capacitor Android platform, verify emulator build.
TASK-003 Implement Node REST API with contract tests.
TASK-004 Provision local PostgreSQL schema and migration tests.
TASK-005 Connect Ionic API client, auth contract and CRUD endpoints.
TASK-006 Full integration, security, regression and Tech Lead approval.

All task IDs are examples. Only explicit Status: approved entries in
that project's .agent/BACKLOG.md are executed.
