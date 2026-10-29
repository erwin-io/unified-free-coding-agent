---
name: node-web-development
description: Build and validate Node.js APIs and vanilla HTML/CSS/JavaScript interfaces.
---
Read AGENTS.md, .agent/ARCHITECTURE.md, DECISIONS.md, BACKLOG.md, HANDOFF.md.
Discover package.json scripts before editing, respect the repository's module system.
Use the test runner to verify API routes and error paths, and inspect the UI.
Keep frontend and API contracts consistent; do not silently introduce a database
or change authentication. Run actual npm test/lint/build checks where present
and record exact exit codes. Treat test evidence as stronger than prior model notes.
