# Automatic provider switching and retry

OpenCode always calls `unified/auto-coder`. The router changes the actual
free cloud provider transparently on **pre-stream** 429/401/403/404/5xx
failures. Direct Gemini is excluded from coding tool calls until thought
signatures can be preserved. If Kilo is unavailable, OpenRouter Free can
take over when it has capacity and supports the requested tools.

The old gateway overestimated context by treating JSON bytes as a tokenizer
and rejected working providers before sending requests. The router no longer
uses that approximation as a hard gate. Actual token/context rejection comes
from the model. OpenCode retains its own configured context window.

The router's `/router/status` exposes per-provider eligibility, request counts,
cooldowns, model IDs and seconds until a locally measured cap expires.
Unavailable responses include `Retry-After` and provider-specific reasons.
These are **local estimates**, not the provider's authoritative quotas.

The bundled OpenCode 2 plugin automatically retries transient gateway errors
(429, 502, 503, 504) with bounded exponential delays, up to OpenCode's own
attempt limit. The router rechecks all eligible free providers at each retry.
This can restore an interrupted turn when a free provider becomes available
quickly. It cannot wait indefinitely or guarantee recovery when all free
providers remain exhausted for hours.

The local supervisor already polls for recovery on explicitly approved
BACKLOG.md tasks when the unattended worker is enabled. It does not
automatically take over arbitrary interactive OpenCode sessions. Do not run
two workers simultaneously on the same Git workspace.

On Windows, after `git pull origin main`, restart the launcher to load the
updated router revision. Then inspect health and capacity:

```powershell
Invoke-RestMethod http://127.0.0.1:4030/health
powershell -ExecutionPolicy Bypass -File .\run.ps1 -Mode status
```

If the error repeats, capture `/router/status` output but redact any local
authentication values. Inspect whether a real provider limit or an upstream
model/credential problem is preventing fallback.
