# Test Node.js Web App

A runnable full-stack smoke-test project for the Unified Free Coding Agent.

- Node.js 20+, no external npm dependencies and no database.
- Frontend: `public/index.html`, `public/styles.css`, `public/app.js`
- Backend: `server.js`, Node built-in HTTP server.
- API: GET /api/health; GET/POST /api/tasks; PATCH/DELETE /api/tasks/:id.
- Storage is in memory only and resets after restarting the process.

Local commands:

```powershell
npm test
npm run lint
npm start
```

Visit http://127.0.0.1:3000 and check http://127.0.0.1:3000/api/health.
The agent launcher can automatically initialize this example at
`C:\Development\test-nodejs-web-app` without overwriting an existing project.

Tasks for autonomous execution belong in `.agent/BACKLOG.md`; start with
`Status: draft` and change to `Status: approved` only when ready.
