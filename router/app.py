"""Compatible Chat Completions gateway; free-only and pre-stream failover.

Stream handoff cannot be safe once response bytes reach the client.
A 429 may also occur inside streamed data and require a new agent turn.
"""
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .config import integer, load_env, providers
from .store import Store

load_env()
ROOT = Path(__file__).resolve().parents[1]
db_path = Path(os.getenv("ROUTER_DB", ".agent-runtime/usage.sqlite3"))
if not db_path.is_absolute():
    db_path = ROOT / db_path
DB = Store(str(db_path))
FREE_PROVIDERS = providers()
KEY = os.getenv("FREE_ROUTER_KEY", "local-agent-only")
RESERVE = min(50, integer("ROUTER_RESERVE_PERCENT", 10))
TIMEOUT = max(15, integer("UPSTREAM_TIMEOUT_SECONDS", 120))
ROUTER_REVISION = "2026-10-30-gemini38"


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=15.0)) as client:
        app.state.client = client
        yield


app = FastAPI(title="Unified Free Coding Router", lifespan=lifespan)


def authorize(value):
    if not value or value != "Bearer " + KEY:
        raise HTTPException(status_code=401, detail="Router key required")


def estimate_tokens(body):
    # Approximation for capacity screening, NOT billable token accounting.
    return max(512, len(json.dumps(body.get("messages", []), ensure_ascii=False)) // 3
               + 1500 + len(json.dumps(body.get("tools", []))) // 3)


def status_for(provider):
    counts = DB.counts(provider.name)
    cooldown, reason = DB.cooldown(provider.name)
    caps = {"minute": provider.minute_cap, "hour": provider.hour_cap, "day": provider.day_cap}
    ratios = {k: round(counts[k] / v, 3) for k, v in caps.items() if v}
    # Avoid burning last requests on new work; reserve is advisory when no backup exists.
    available = (cooldown == 0 and all(counts[k] < v for k, v in caps.items() if v))
    level = ("critical" if any(x >= .95 for x in ratios.values()) else
             "handoff" if any(x >= .85 for x in ratios.values()) else
             "warning" if any(x >= .70 for x in ratios.values()) else "healthy")
    return {"name": provider.name, "model": provider.model, "eligible": available,
            "counts": counts, "limits": caps, "utilization": ratios,
            "warning": level, "cooldown_seconds": cooldown, "reason": reason,
            "token_totals": DB.usage(provider.name)}


def candidates(body):
    approx = estimate_tokens(body)
    available = [p for p in FREE_PROVIDERS
                 if approx < p.context and status_for(p)["eligible"]]
    if len(available) > 1:
        available.sort(key=lambda p: (
            status_for(p)["warning"] in ("handoff", "critical"),
            FREE_PROVIDERS.index(p)))
    return available


@app.get("/health")
def health():
    return {"status": "ok", "mode": "FREE_ONLY", "revision": ROUTER_REVISION, "providers": [p.name for p in FREE_PROVIDERS]}


@app.get("/router/status")
def status(authorization: str | None = Header(default=None)):
    authorize(authorization)
    return {"mode": "FREE_ONLY", "providers": [status_for(p) for p in FREE_PROVIDERS],
            "any_available": any(status_for(p)["eligible"] for p in FREE_PROVIDERS)}


@app.get("/v1/models")
def models(authorization: str | None = Header(default=None)):
    authorize(authorization)
    return {"object": "list", "data": [{"id": "auto-coder", "object": "model",
                                        "owned_by": "unified-local-router"}]}


@app.post("/v1/chat/completions")
async def chat(req: Request, authorization: str | None = Header(default=None)):
    authorize(authorization)
    body = await req.json()
    if not isinstance(body, dict) or body.get("model") != "auto-coder":
        raise HTTPException(status_code=400, detail="Only auto-coder is allowed")
    if not isinstance(body.get("messages"), list) or not body["messages"]:
        raise HTTPException(status_code=400, detail="messages must be non-empty")
    stream = body.get("stream", False) is True
    options = candidates(body)
    if not options:
        return JSONResponse(status_code=503, content={"error": {
            "code": "FREE_CAPACITY_EXHAUSTED",
            "message": "No free model is currently eligible. Preserve your checkpoint and retry later."}})
    errors = []
    for p in options:
        payload = dict(body)
        payload["model"] = p.model
        headers = {"Content-Type": "application/json"}
        if p.key:
            headers["Authorization"] = "Bearer " + p.key
        start = time.monotonic()
        try:
            # stream=True holds provider response open until forwarded / consumed.
            upstream = await req.app.state.client.send(
                req.app.state.client.build_request("POST", p.url, json=payload, headers=headers),
                stream=True)
        except httpx.HTTPError:
            DB.add(p.name, 599, int((time.monotonic() - start) * 1000))
            DB.block(p.name, 30, "network_error")
            errors.append(p.name + ": network error")
            continue
        elapsed = int((time.monotonic() - start) * 1000)
        if upstream.status_code in (429, 500, 502, 503, 504):
            DB.add(p.name, upstream.status_code, elapsed)
            DB.block(p.name, 90 if upstream.status_code == 429 else 30,
                     "HTTP_" + str(upstream.status_code))
            errors.append(p.name + ": HTTP " + str(upstream.status_code))
            await upstream.aclose()
            continue
        if upstream.status_code >= 400:
            info = (await upstream.aread())[:800].decode("utf-8", errors="replace")
            await upstream.aclose()
            DB.add(p.name, upstream.status_code, elapsed)
            # A malformed tool request should NOT get blindly replayed across providers.
            return JSONResponse(status_code=upstream.status_code,
                                content={"error": {"code": "UPSTREAM_REJECTED",
                                                   "message": p.name + ": " + info}})
        if stream:
            DB.add(p.name, upstream.status_code, elapsed)
            async def forward(response=upstream):
                try:
                    async for chunk in response.aiter_raw():
                        yield chunk
                finally:
                    await response.aclose()
            return StreamingResponse(forward(), media_type="text/event-stream",
                                     headers={"X-Local-Router-Provider": p.name,
                                              "Cache-Control": "no-cache"})
        data = await upstream.aread()
        await upstream.aclose()
        try:
            obj = json.loads(data)
            usage = obj.get("usage") or {}
            DB.add(p.name, upstream.status_code, elapsed,
                   usage.get("prompt_tokens"), usage.get("completion_tokens"))
            return JSONResponse(content=obj, headers={"X-Local-Router-Provider": p.name})
        except (ValueError, TypeError):
            DB.add(p.name, 502, elapsed)
            return JSONResponse(status_code=502, content={"error": {
                "code": "UPSTREAM_INVALID_JSON", "message": "Provider returned non-JSON"}})
    return JSONResponse(status_code=503, content={"error": {
        "code": "ALL_PROVIDERS_FAILED", "message": "; ".join(errors)}})
