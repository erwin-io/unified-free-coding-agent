# Application process lifecycle

When the owner tells you to stop the project application, never run
taskkill /IM node.exe or Stop-Process -Name node.

For the managed local Node.js demo, inspect and stop just the selected app:

powershell -ExecutionPolicy Bypass -File "$env:UNIFIED_AGENT_ROOT\run.ps1" -Mode status-app
powershell -ExecutionPolicy Bypass -File "$env:UNIFIED_AGENT_ROOT\run.ps1" -Mode stop-app

To start it again without restarting OpenCode:
powershell -ExecutionPolicy Bypass -File "$env:UNIFIED_AGENT_ROOT\run.ps1" -Mode start-app

If process ownership is unverified, request explicit owner approval before
-Mode stop-app -AllowUntracked. The AI router on 4030 is never an app target.
This command currently handles only the Node demo on port 3000.
