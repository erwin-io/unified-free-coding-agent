"""Verified-free-only provider allowlist and local environment loading."""
import os
from dataclasses import dataclass
from pathlib import Path


def load_env():
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def integer(name, default):
    try:
        return max(0, int(os.environ.get(name, default)))
    except ValueError:
        return default


def flag(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Provider:
    name: str
    url: str
    model: str
    key: str
    minute_cap: int = 0
    hour_cap: int = 0
    day_cap: int = 0
    context: int = 24000


def providers():
    result = []
    if flag("KILO_ENABLED", True):
        result.append(Provider(
            "kilo", "https://ai-gateway.kilo.ai/api/v1/chat/completions",
            "kilo-auto/free", os.getenv("KILO_API_KEY", ""),
            hour_cap=integer("KILO_HOURLY_CAP", 200), context=30000))
    gemini = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    # Never permit arbitrary paid-model IDs through env.
    if gemini and model in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
        result.append(Provider(
            "gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            model, gemini, minute_cap=integer("GEMINI_MINUTE_CAP", 0),
            day_cap=integer("GEMINI_DAILY_CAP", 0), context=60000))
    openrouter = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter:
        result.append(Provider(
            "openrouter", "https://openrouter.ai/api/v1/chat/completions",
            "openrouter/free", openrouter, minute_cap=20,
            day_cap=min(integer("OPENROUTER_DAILY_CAP", 50), 50), context=24000))
    order = [s.strip() for s in os.getenv("PROVIDER_ORDER", "kilo,gemini,openrouter").split(",")]
    return sorted(result, key=lambda p: order.index(p.name) if p.name in order else 99)
